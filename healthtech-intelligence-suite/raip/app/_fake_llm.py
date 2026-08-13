"""Deterministic fake LLM + hashed embeddings for CI and demos."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeChatModel(BaseChatModel):
    model_name: str = Field(default="raip-fake")

    @property
    def _llm_type(self) -> str:
        return "raip-fake"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        blob = " ".join(str(m.content) for m in messages)
        payload = self._reply(blob)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=payload))])

    def _reply(self, text: str) -> str:
        lowered = text.lower()
        if "recommend crispr" in lowered or "crispr gene editing as first-line" in lowered:
            return (
                "## Clinical Management Recommendations\n\n"
                "EVIDENCE GAP\n\n"
                "The available approved sources do not provide sufficient evidence "
                "to support CRISPR gene editing as therapy for type 2 diabetes.\n\n"
                "Recommended action: Author review / additional authoritative source required.\n"
            )
        if "synthesize an evidence map" in lowered:
            return json.dumps(
                {
                    "summary": "Authoritative sources prefer metformin as first-line adult T2DM therapy unless contraindicated. Older guidance recommending sulfonylurea first-line is superseded.",
                    "conflicts": ["v1 sulfonylurea first-line vs v2 metformin first-line"],
                    "preferred_authority": "guideline v2",
                }
            )
        if "editorial" in lowered or "readability" in lowered:
            return "Editorial pass applied. Evidence grounding was not altered."
        if "judge" in lowered or "groundedness" in lowered:
            unsupported = "evidence gap" in lowered or "unsupported" in lowered
            return json.dumps(
                {
                    "grounding": 0.42 if unsupported else 0.96,
                    "citation_correctness": 0.95,
                    "completeness": 0.9,
                    "medical_safety": 0.5 if "drugz" in lowered else 0.97,
                    "regulatory_consistency": 0.94,
                    "instruction_adherence": 0.96,
                    "feedback": "Deterministic fake judge.",
                }
            )
        if "draft the section" in lowered or "author request:" in lowered or "write the section" in lowered:
            if "drugz" in lowered and "metformin" not in lowered:
                return (
                    "## Clinical Management Recommendations\n\n"
                    "EVIDENCE GAP\n\n"
                    "The available approved sources do not provide sufficient evidence "
                    "to support DrugZ as first-line therapy.\n"
                )
            return (
                "## Purpose\n"
                "This section summarizes pharmacologic recommendations for adults with type 2 diabetes "
                "using only approved source documents.\n\n"
                "## Clinical Management Recommendations\n"
                "First-line pharmacologic therapy for adults with type 2 diabetes is metformin "
                "unless contraindicated. [1]\n\n"
                "Promotional or clinical claims must be substantiated by the cited evidence. [2]\n\n"
                "## Monitoring\n"
                "Reassess glycemic control after therapy initiation according to the cited guideline. [1]\n\n"
                "## Limitations\n"
                "This draft is not a patient-specific treatment plan and does not authorize autonomous "
                "prescribing.\n\n"
                "## References\n"
                "[1] Northstar Endocrine Consortium T2DM Guideline v2 (2024).\n"
                "[2] Regulatory substantiation guidance (2024).\n"
            )
        return "Insufficient evidence — requires author review."


class FakeEmbeddings:
    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256((text or "").encode("utf-8")).digest()
        vals = [(digest[i % len(digest)] / 255.0) for i in range(self.dim)]
        for tok in (text or "").lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest()[:8], 16)
            vals[h % self.dim] = min(1.0, vals[h % self.dim] + 0.18)
        return vals


def is_fake_chat_model(name: str) -> bool:
    n = (name or "").strip().lower()
    return n in {"fake", "raip-fake"} or n.startswith("fake")


def is_fake_embeddings(name: str) -> bool:
    return is_fake_chat_model(name)
