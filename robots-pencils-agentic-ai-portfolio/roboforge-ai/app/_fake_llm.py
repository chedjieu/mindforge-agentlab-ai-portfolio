"""Deterministic offline LLM for RoboForge."""

from __future__ import annotations

import hashlib
import json
import math
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


def _last_human(messages: list[BaseMessage]) -> str:
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            c = m.content
            return c if isinstance(c, str) else json.dumps(c)
    return ""


def _system(messages: list[BaseMessage]) -> str:
    for m in messages:
        if isinstance(m, SystemMessage):
            c = m.content
            return c if isinstance(c, str) else json.dumps(c)
    return ""


def _domain(text: str) -> str:
    low = text.lower()
    # Prefer agentic when AgentCore / multi-agent is the primary ask
    if any(k in low for k in ("agentcore", "multi-agent", "agentic", "velocity pod")):
        return "agentic"
    if any(k in low for k in ("migrate", "mainframe", "legacy java", ".net monolith")):
        return "migration"
    if any(k in low for k in ("rag", "knowledge base", "retrieval", "graphrag")):
        return "rag"
    if any(k in low for k in ("modernize", "serverless", "ecs to", "lift")):
        return "modernize"
    return "agentic"


def _intake(text: str) -> dict:
    domain = _domain(text)
    return {
        "domain": domain,
        "objectives": ["Ship production agentic AI on AWS Bedrock/AgentCore", "Cut discovery cycle time"],
        "stakeholders": ["CIO", "Security", "Delivery lead"],
        "constraints": ["HITL before go-live", "AWS-first", "No live PII in demos"],
        "risks": ["Legacy coupling", "Compliance gaps"],
        "summary": f"Intake classified as {domain} engagement",
    }


def _blueprint(text: str) -> dict:
    domain = _domain(text)
    return {
        "title": f"{domain.title()} Bedrock AgentCore blueprint",
        "summary": (
            "LangGraph supervisor on Bedrock AgentCore with hybrid RAG, Neo4j GraphRAG, "
            "HITL gates, and audit/delivery packs."
        ),
        "architecture": [
            "Amazon Bedrock + AgentCore runtime",
            "Tenant/engagement-scoped RAG + Neo4j",
            "FastAPI approval console + Slack HITL",
        ],
        "rag_design": ["hybrid dense+BM25", "GraphRAG for dependencies", "citation required"],
        "agent_topology": ["supervisor", "specialist workers", "judge_gate", "hitl"],
        "citations": ["ev-1", "ev-2"],
        "risk_flags": [],
    }


def _judge(text: str) -> dict:
    low = text.lower()
    grounded = 0.4 if "invented vpc" in low or "hallucin" in low else 0.9
    security = 0.4 if "skip encryption" in low else 0.92
    cost = 0.85
    arch = 0.88
    return {
        "architecture": arch,
        "groundedness": grounded,
        "security_compliance": security,
        "cost_realism": cost,
        "pass": arch >= 0.85 and grounded >= 0.85 and security >= 0.9 and cost >= 0.8,
        "notes": "fake judge",
    }


class FakeRFAIChatModel(BaseChatModel):
    model_name: str = "fake-rfai"
    temperature: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "fake-rfai"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        human = _last_human(messages)
        system = _system(messages).lower()
        if "intake" in system or "objectives" in system:
            payload = _intake(human)
        elif "judge" in system or "groundedness" in system:
            payload = _judge(human + " " + system)
        elif "estimate roi" in system or ("roi" in system and "cost" in system):
            payload = {
                "monthly_infra_usd": 4200,
                "monthly_token_usd": 1800,
                "annual_savings_usd": 480000,
                "payback_months": 4,
                "notes": "Velocity Pod time compression + reuse",
            }
        elif "architect" in system or "draft a bedrock" in system:
            payload = _blueprint(human)
        else:
            payload = {"ok": True}
        msg = AIMessage(content=json.dumps(payload), id=str(uuid4()))
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def with_structured_output(self, schema: type[BaseModel], **kwargs: Any):  # type: ignore[override]
        def _invoke(input_value: Any):
            if isinstance(input_value, list):
                messages = input_value
            elif isinstance(input_value, dict) and "messages" in input_value:
                messages = input_value["messages"]
            else:
                messages = [HumanMessage(content=str(input_value))]
            raw = self._generate(messages).generations[0].message.content
            data = json.loads(raw) if isinstance(raw, str) else raw
            try:
                return schema.model_validate(data)
            except Exception:
                fields = getattr(schema, "model_fields", {})
                merged = {k: data.get(k, getattr(f, "default", None)) for k, f in fields.items()}
                return schema.model_validate({k: v for k, v in merged.items() if v is not None})

        return RunnableLambda(_invoke)


class FakeRFAIEmbeddings(Embeddings):
    dim: int = 1024

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256((text or "").encode()).digest()
        vals: list[float] = []
        while len(vals) < self.dim:
            for i in range(0, len(digest), 4):
                if len(vals) >= self.dim:
                    break
                chunk = digest[i : i + 4].ljust(4, b"\x00")
                n = struct.unpack(">I", chunk)[0]
                vals.append((n / 2**32) * 2 - 1)
            digest = hashlib.sha256(digest).digest()
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]


def fake_chat_model(**kwargs: Any) -> FakeRFAIChatModel:
    return FakeRFAIChatModel(**kwargs)


def fake_embeddings(**kwargs: Any) -> FakeRFAIEmbeddings:
    return FakeRFAIEmbeddings(**kwargs)
