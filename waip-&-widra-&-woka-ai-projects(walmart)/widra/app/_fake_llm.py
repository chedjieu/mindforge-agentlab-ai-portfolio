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
    """Heuristic responses for document retrieval queries."""

    model_name: str = Field(default="widra-fake")

    @property
    def _llm_type(self) -> str:
        return "widra-fake"

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
        if "rewrite" in text or "expand" in text:
            return json.dumps({"rewritten_query": text[:200]})

        return json.dumps(
            {
                "answer": (
                    "Based on retrieved Walmart policy documents, damaged goods returns "
                    "require manager approval within 30 days. See cited source for details."
                ),
                "citations": [
                    {
                        "doc_id": "sample-001",
                        "title": "US Return Policy",
                        "page": 2,
                        "snippet": "Damaged merchandise may be returned within 30 days...",
                    }
                ],
                "confidence": 0.91,
            }
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
        for tok in text.lower().split():
            h = int(hashlib.md5(tok.encode()).hexdigest()[:8], 16)
            vals[h % self.dim] = min(1.0, vals[h % self.dim] + 0.15)
        return vals
