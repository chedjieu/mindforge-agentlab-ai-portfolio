"""Deterministic fake LLM for offline demos and CI."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeChatModel(BaseChatModel):
    model_name: str = Field(default="hedip-fake")

    @property
    def _llm_type(self) -> str:
        return "hedip-fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = " ".join(str(m.content) for m in messages).lower()
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self._reply(text)))])

    def _reply(self, text: str) -> str:
        if "classify domain" in text or "intent router" in text:
            for d in (
                "prior_auth",
                "claims",
                "clinical_cds",
                "care_coord",
                "knowledge",
                "fraud",
                "pop_health",
                "rcm",
            ):
                if d.replace("_", " ") in text or d in text:
                    return json.dumps({"domain": d, "sensitivity": "sensitive" if d in (
                        "prior_auth", "claims", "clinical_cds", "fraud"
                    ) else "normal"})
            if any(k in text for k in ("prior auth", "prior-auth", "mri", "biologic", "authorization")):
                return json.dumps({"domain": "prior_auth", "sensitivity": "sensitive"})
            if any(k in text for k in ("claim", "icd", "cpt", "denial", "appeal")):
                return json.dumps({"domain": "claims", "sensitivity": "sensitive"})
            if any(k in text for k in ("treatment plan", "cds", "medication interaction")):
                return json.dumps({"domain": "clinical_cds", "sensitivity": "sensitive"})
            if any(k in text for k in ("discharge", "care coord", "readmission")):
                return json.dumps({"domain": "care_coord", "sensitivity": "normal"})
            if any(k in text for k in ("fraud", "upcoding", "collusion")):
                return json.dumps({"domain": "fraud", "sensitivity": "sensitive"})
            if any(k in text for k in ("population", "readmit", "sepsis risk")):
                return json.dumps({"domain": "pop_health", "sensitivity": "normal"})
            if any(k in text for k in ("coding", "documentation", "revenue")):
                return json.dumps({"domain": "rcm", "sensitivity": "normal"})
            return json.dumps({"domain": "knowledge", "sensitivity": "normal"})

        if "evaluate" in text and "safety_score" in text:
            return json.dumps(
                {
                    "safety_score": 0.93,
                    "groundedness": 0.92,
                    "citation_coverage": 0.94,
                    "hallucination_risk": 0.06,
                    "notes": "Claims aligned to retrieved evidence.",
                }
            )

        if "prior auth" in text or "medical necessity" in text:
            if "incomplete" in text or "need_info" in text or "physical therapy" in text:
                decision = "need_info"
            elif "step therapy" in text or "deny" in text:
                decision = "deny"
            else:
                decision = "approve"
            return json.dumps(
                {
                    "decision": decision,
                    "confidence": 0.91,
                    "explanation": f"Prior auth recommendation: {decision} based on policy and clinical evidence.",
                    "missing_docs": ["PT notes"] if decision == "need_info" else [],
                    "alternatives": ["preferred formulary agent"] if decision == "deny" else [],
                }
            )

        if "denial" in text or "claim risk" in text:
            return json.dumps(
                {
                    "decision": "fix_first",
                    "denial_risk": 0.78,
                    "issues": ["documentation gap", "possible upcoding"],
                    "appeal_draft": "Appeal: medical necessity supported by attached notes.",
                }
            )

        if "treatment plan" in text or "clinical cds" in text:
            return (
                "## Personalized Treatment Plan\n\n"
                "### Goals\n- Improve disease control\n\n"
                "### Interventions\n- Optimize therapy per guidelines\n"
                "- Address medication safety\n\n"
                "### Monitoring\n- Labs in 8-12 weeks\n\n"
                "### Follow-up\n- Clinic follow-up\n"
            )

        return (
            "Based on retrieved healthcare policies, guidelines, and graph evidence, "
            "here is an explainable decision recommendation with citations."
        )


class FakeEmbeddings:
    def __init__(self, dim: int = 64):
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vals = [(digest[i % len(digest)] / 255.0) for i in range(self.dim)]
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest()[:8], 16)
            vals[h % self.dim] = min(1.0, vals[h % self.dim] + 0.15)
        return vals


def is_fake(name: str) -> bool:
    n = (name or "").strip().lower()
    return n in ("fake", "hedip-fake") or n.startswith("fake")
