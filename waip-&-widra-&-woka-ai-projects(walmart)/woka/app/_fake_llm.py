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
    model_name: str = Field(default="woka-fake")

    @property
    def _llm_type(self) -> str:
        return "woka-fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = " ".join(str(m.content) for m in messages).lower()
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self._reply(text)))])

    def _reply(self, text: str) -> str:
        if "groundedness" in text or "validator" in text or "judge" in text:
            return json.dumps(
                {
                    "groundedness": 0.96,
                    "citation_coverage": 0.97,
                    "hallucination_risk": 0.01,
                    "confidence": 0.94,
                    "notes": "Claims aligned to SQL inventory and contingency SOP citations.",
                }
            )

        if any(k in text for k in ("hurricane", "disruption", "stock out", "southeast", "dc")):
            return json.dumps(
                {
                    "answer": (
                        "Southeast DC closures (ATL-01, JAX-02) affect suppliers Acme Logistics and "
                        "GulfFresh Produce. SKUs TV-55-4K and MILK-GAL are delayed. Within 300 miles, "
                        "DC-MEM holds 12,400 units of TV-55-4K and 8,200 of MILK-GAL. Contracts "
                        "C-ACME-2024 and C-GULF-2023 permit alternate sourcing with 48h notice. "
                        "Stores S-1001 and S-1044 are projected to stock out of MILK-GAL within 48 hours."
                    ),
                    "agents_used": ["retrieval", "sql", "internet", "compliance", "citation"],
                    "citations": [
                        {
                            "doc_id": "sc-sop-001",
                            "title": "Southeast DC Contingency SOP",
                            "page": 3,
                            "section": "Alternate sourcing",
                            "snippet": "Contracts with force-majeure alternate sourcing require 48h notice...",
                            "confidence": 0.93,
                        },
                        {
                            "doc_id": "sql:inventory",
                            "title": "Inventory within 300mi of ATL",
                            "page": 0,
                            "section": "query",
                            "snippet": "DC-MEM TV-55-4K=12400 MILK-GAL=8200",
                            "confidence": 0.97,
                        },
                        {
                            "doc_id": "ext:weather",
                            "title": "NOAA Hurricane Advisory (mock)",
                            "page": 1,
                            "section": "Impact zone",
                            "snippet": "SE coastal DCs under evacuation / closure order...",
                            "confidence": 0.9,
                            "source_type": "external",
                        },
                    ],
                    "confidence": 0.92,
                }
            )

        return json.dumps(
            {
                "answer": (
                    "Based on authorized Walmart knowledge sources, refer to the cited policy "
                    "or operational document for the definitive procedure."
                ),
                "agents_used": ["retrieval", "citation"],
                "citations": [
                    {
                        "doc_id": "policy-001",
                        "title": "General Operations Policy",
                        "page": 1,
                        "section": "Overview",
                        "snippet": "Associates must follow the latest effective policy version...",
                        "confidence": 0.85,
                    }
                ],
                "confidence": 0.85,
            }
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
