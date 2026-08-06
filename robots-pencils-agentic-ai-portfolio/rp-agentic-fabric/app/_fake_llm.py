"""Deterministic offline stand-in for chat models + embeddings (RPADF)."""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from typing import Any
from uuid import uuid4

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel


def is_fake_chat_model(name: str) -> bool:
    return (name or "").strip().lower() in ("fake", "stub", "offline")


def is_fake_embeddings(name: str) -> bool:
    return (name or "").strip().lower() in ("fake", "stub", "offline")


def _last_human_text(messages: list[BaseMessage]) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            c = m.content
            return c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
    return ""


def _system_text(messages: list[BaseMessage]) -> str:
    for m in messages:
        if isinstance(m, SystemMessage):
            c = m.content
            return c if isinstance(c, str) else json.dumps(c, ensure_ascii=False)
    return ""


def _detect_vertical(text: str) -> str:
    low = text.lower()
    if any(k in low for k in ("student", "ferpa", "sis", "canvas", "edtech", "enrollment")):
        return "edtech"
    if any(k in low for k in ("hipaa", "patient", "fhir", "phi", "clinical", "healthcare")):
        return "healthcare"
    if any(k in low for k in ("glba", "bank", "fintech", "soc2", "pci", "finserv", "account")):
        return "finserv"
    if any(k in low for k in ("retail", "merchant", "sku", "personalization", "shopper")):
        return "retail"
    return "edtech"


def _router_payload(text: str) -> dict:
    vertical = _detect_vertical(text)
    sensitivity = "regulated" if vertical in ("healthcare", "finserv") else "sensitive"
    if vertical == "retail":
        sensitivity = "normal"
    return {
        "vertical": vertical,
        "sensitivity": sensitivity,
        "policy_pack_id": f"{vertical}-v1",
        "rationale": f"Matched keywords for {vertical}",
    }


def _plan_payload(text: str) -> dict:
    vertical = _detect_vertical(text)
    return {
        "title": f"{vertical.title()} engagement plan",
        "summary": (
            f"Propose a tenant-scoped {vertical} agentic delivery pattern with "
            "policy-pack guardrails, reusable IP sanitization, and an audit pack."
        ),
        "architecture": [
            "LangGraph supervisor on Bedrock AgentCore",
            "Tenant-scoped RAG + Neo4j provenance",
            "HITL approval before production promote",
        ],
        "playbook_steps": [
            "Load compliance policy pack",
            "Sanitize reusable components via Reuse-Broker",
            "Assemble worker graph under allowlist",
            "Run judge gate + HITL",
            "Publish audit/provenance pack",
        ],
        "citations": ["ev-1", "ev-2"],
        "risk_flags": [],
        "recommended_action": "escalate" if vertical in ("healthcare", "finserv") else "publish",
    }


def _judge_payload(text: str) -> dict:
    # Score leakage from the Draft: section only (evidence may mention RiskFlag names).
    low_full = text.lower()
    draft_idx = low_full.find("draft:")
    draft_part = low_full[draft_idx:] if draft_idx >= 0 else low_full
    leakage = (
        0.0
        if any(
            k in draft_part
            for k in ("tenant-other", "tenant-rival", "acme-health-secret", "leaked-tenant")
        )
        else 1.0
    )
    compliance = 0.92
    faithfulness = 0.88
    if "invented" in low_full or "hallucin" in low_full:
        faithfulness = 0.4
    return {
        "compliance": compliance,
        "faithfulness": faithfulness,
        "leakage": leakage,
        "pass": compliance >= 0.9 and faithfulness >= 0.85 and leakage >= 1.0,
        "notes": "Fake judge scores for offline demo",
    }


class FakeRPADFChatModel(BaseChatModel):
    """Deterministic chat model for offline RPADF demos and evals."""

    model_name: str = "fake-rpadf"
    temperature: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "fake-rpadf"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        human = _last_human_text(messages)
        system = _system_text(messages).lower()
        schema = kwargs.get("schema") or kwargs.get("response_format")

        if "vertical" in system or "router" in system or "classify" in system:
            payload = _router_payload(human)
        elif "judge" in system or "compliance score" in system or "leakage" in system:
            payload = _judge_payload(human + " " + system)
        elif "engagement plan" in system or "synthesizer" in system or "playbook" in system:
            payload = _plan_payload(human)
        else:
            payload = {"ok": True, "echo": human[:200]}

        content = json.dumps(payload, ensure_ascii=False)
        if schema is not None and isinstance(schema, type) and issubclass(schema, BaseModel):
            # structured path handled via with_structured_output wrapper
            pass
        msg = AIMessage(content=content, id=str(uuid4()))
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def with_structured_output(self, schema: type[BaseModel], **kwargs: Any):  # type: ignore[override]
        def _invoke(input_value: Any):
            if isinstance(input_value, list):
                messages = input_value
            elif isinstance(input_value, dict) and "messages" in input_value:
                messages = input_value["messages"]
            else:
                messages = [HumanMessage(content=str(input_value))]
            result = self._generate(messages)
            raw = result.generations[0].message.content
            data = json.loads(raw) if isinstance(raw, str) else raw
            # Fill missing fields with defaults from schema if needed
            try:
                return schema.model_validate(data)
            except Exception:
                # Best-effort merge for router/plan/judge shapes
                fields = getattr(schema, "model_fields", {})
                merged = {k: data.get(k) for k in fields}
                for k, f in fields.items():
                    if merged.get(k) is None and f.default is not None:
                        merged[k] = f.default
                return schema.model_validate({k: v for k, v in merged.items() if v is not None})

        return RunnableLambda(_invoke)


class FakeRPADFEmbeddings(Embeddings):
    """Deterministic hashed embeddings (1024-dim)."""

    dim: int = 1024

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256((text or "").encode("utf-8")).digest()
        vals: list[float] = []
        while len(vals) < self.dim:
            for i in range(0, len(digest), 4):
                if len(vals) >= self.dim:
                    break
                chunk = digest[i : i + 4]
                if len(chunk) < 4:
                    chunk = chunk + b"\x00" * (4 - len(chunk))
                n = struct.unpack(">I", chunk)[0]
                vals.append((n / 2**32) * 2 - 1)
            digest = hashlib.sha256(digest).digest()
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]


def fake_chat_model(**kwargs: Any) -> FakeRPADFChatModel:
    return FakeRPADFChatModel(**kwargs)


def fake_embeddings(**kwargs: Any) -> FakeRPADFEmbeddings:
    return FakeRPADFEmbeddings(**kwargs)
