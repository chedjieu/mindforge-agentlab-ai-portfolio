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
    """Heuristic responses keyed off the last human message."""

    model_name: str = Field(default="waip-fake")

    @property
    def _llm_type(self) -> str:
        return "waip-fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = " ".join(str(m.content) for m in messages).lower()
        payload = self._reply(text)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=payload))])

    def _reply(self, text: str) -> str:
        if "intent" in text or "planner" in text or "classify" in text:
            intents: list[str] = []
            workers: list[str] = []
            if any(k in text for k in ("paycheck", "pay", "payroll", "short", "overtime", "w-2")):
                intents.append("payroll_discrepancy")
                workers.append("payroll")
            if any(k in text for k in ("leave", "fmla", "pto", "medical leave", "loa")):
                intents.append("medical_leave")
                workers.append("leave")
            if any(k in text for k in ("benefit", "insurance", "hsa", "401")):
                intents.append("benefits")
                workers.append("benefits")
            if any(k in text for k in ("ticket", "open a", "service now", "servicenow")):
                intents.append("ticket_creation")
                workers.append("ticket")
            if any(k in text for k in ("policy", "handbook", "dress", "attendance")) or not workers:
                intents.append("hr_policy")
                workers.append("hr")
            workers.append("search")
            # dedupe preserve order
            seen: set[str] = set()
            workers = [w for w in workers if not (w in seen or seen.add(w))]  # type: ignore[func-returns-value]
            return json.dumps({"intents": intents or ["hr_policy"], "workers": workers or ["hr", "search"]})

        if "groundedness" in text or "validator" in text or "judge" in text:
            return json.dumps(
                {
                    "groundedness": 0.92,
                    "citation_coverage": 0.94,
                    "confidence": 0.88,
                    "hallucination_risk": 0.08,
                    "notes": "Claims aligned to retrieved payroll and leave policies.",
                }
            )

        if "compliance" in text:
            return json.dumps(
                {
                    "compliance_score": 0.95,
                    "pii_exposure": 0.05,
                    "action_authorized": True,
                    "notes": "ABAC OK; mutating action requires HITL.",
                }
            )

        # default draft helper
        return (
            "Based on retrieved Walmart leave and payroll policies, unpaid medical leave "
            "hours are excluded from regular pay for the affected pay period. "
            "If hours were coded incorrectly, a payroll ticket should be opened."
        )


class FakeEmbeddings:
    """Hash-based embedding vectors for offline hybrid search."""

    def __init__(self, dim: int = 64):
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vals = [(digest[i % len(digest)] / 255.0) for i in range(self.dim)]
        # light bag-of-words mixing for better lexical affinity in fake space
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest()[:8], 16)
            vals[h % self.dim] = min(1.0, vals[h % self.dim] + 0.15)
        return vals
