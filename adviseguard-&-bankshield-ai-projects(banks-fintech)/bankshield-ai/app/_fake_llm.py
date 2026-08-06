"""Deterministic offline stand-in for chat + embeddings (`BANKSHIELD_MODEL=fake`)."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Any, ClassVar
from uuid import uuid4

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel


def is_fake_chat_model(name: str) -> bool:
    return (name or "").strip().lower() in {"fake", "fake_chat", "none"}


def is_fake_embeddings(name: str) -> bool:
    return (name or "").strip().lower() in {"fake", "fake_embeddings", "none"}


class FakeBankShieldChatModel(BaseChatModel):
    """Minimal stub chat model for offline dry-runs."""

    model_name: str = "fake-bankshield"
    temperature: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "fake-bankshield"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        content = (
            '{"fraud_types":["wire","mule"],"payment_rail":"wire",'
            '"sensitivity":"sensitive","needs_graph":true,"needs_identity":true,'
            '"confidence":0.9,"rationale":"fake stub"}'
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def bind_tools(self, tools: Any, **kwargs: Any) -> FakeBankShieldChatModel:
        return self

    def with_structured_output(self, schema: type[BaseModel] | dict, **kwargs: Any):
        def _invoke(messages: Any, _schema: type[BaseModel] = schema):  # type: ignore[assignment]
            if isinstance(_schema, type) and issubclass(_schema, BaseModel):
                fields = {k: v for k, v in _schema.model_fields.items()}
                data: dict[str, Any] = {}
                for name, field in fields.items():
                    ann = str(field.annotation)
                    if "float" in ann:
                        data[name] = 0.9
                    elif "bool" in ann:
                        data[name] = True
                    elif "list" in ann and "fraud" in ann.lower():
                        data[name] = ["wire", "mule"]
                    elif "list" in ann:
                        data[name] = []
                    elif "Literal" in ann and "wire" in ann:
                        data[name] = "wire"
                    elif "Literal" in ann and "sensitive" in ann:
                        data[name] = "sensitive"
                    elif "Literal" in ann and "high" in ann:
                        data[name] = "high"
                    elif "Literal" in ann and "escalate" in ann:
                        data[name] = "escalate"
                    else:
                        data[name] = "fake"
                return _schema(**data)
            return {"ok": True}

        return RunnableLambda(_invoke)


class FakeBankShieldEmbeddings(Embeddings):
    """Deterministic hashed 1024-dim vectors for offline ingest/search."""

    dim: ClassVar[int] = 1024

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        digest = hashlib.sha256((text or "").encode("utf-8")).digest()
        vals: list[float] = []
        while len(vals) < self.dim:
            digest = hashlib.sha256(digest + struct.pack("I", len(vals))).digest()
            for i in range(0, len(digest), 4):
                if len(vals) >= self.dim:
                    break
                (n,) = struct.unpack("I", digest[i : i + 4])
                vals.append((n / 2**32) * 2 - 1)
        norm = math.sqrt(sum(v * v for v in vals)) or 1.0
        return [v / norm for v in vals]


def fake_chat_model(**kwargs: Any) -> FakeBankShieldChatModel:
    return FakeBankShieldChatModel(**{k: v for k, v in kwargs.items() if k in ("temperature",)})


def fake_embeddings(**kwargs: Any) -> FakeBankShieldEmbeddings:
    _ = kwargs
    return FakeBankShieldEmbeddings()


__all__ = [
    "FakeBankShieldChatModel",
    "FakeBankShieldEmbeddings",
    "fake_chat_model",
    "fake_embeddings",
    "is_fake_chat_model",
    "is_fake_embeddings",
    "uuid4",
]
