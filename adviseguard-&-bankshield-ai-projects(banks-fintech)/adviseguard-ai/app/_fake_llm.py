"""Deterministic offline stand-in (`ADVISEGUARD_MODEL=fake`)."""

from __future__ import annotations

import hashlib
import math
import struct
from typing import Any, ClassVar

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


class FakeAdviseGuardChatModel(BaseChatModel):
    model_name: str = "fake-adviseguard"
    temperature: float = 0.0

    @property
    def _llm_type(self) -> str:
        return "fake-adviseguard"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        content = (
            '{"intent":"advice","needs_graph":true,"needs_rag":true,'
            '"run_advisor":true,"run_fraud":false,"run_support":false,'
            '"confidence":0.9,"rationale":"fake stub"}'
        )
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])

    def bind_tools(self, tools: Any, **kwargs: Any) -> FakeAdviseGuardChatModel:
        return self

    def with_structured_output(self, schema: type[BaseModel] | dict, **kwargs: Any):
        def _invoke(messages: Any, _schema: type[BaseModel] = schema):  # type: ignore[assignment]
            if isinstance(_schema, type) and issubclass(_schema, BaseModel):
                data: dict[str, Any] = {}
                for name, field in _schema.model_fields.items():
                    ann = str(field.annotation)
                    if "float" in ann:
                        data[name] = 0.9
                    elif "bool" in ann:
                        data[name] = True
                    elif "list" in ann:
                        data[name] = []
                    elif "Literal" in ann and "advice" in ann:
                        data[name] = "advice"
                    elif "Literal" in ann and "moderate" in ann:
                        data[name] = "moderate"
                    elif "Literal" in ann and "high" in ann:
                        data[name] = "high"
                    else:
                        data[name] = "fake"
                return _schema(**data)
            return {"ok": True}

        return RunnableLambda(_invoke)


class FakeAdviseGuardEmbeddings(Embeddings):
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


def fake_chat_model(**kwargs: Any) -> FakeAdviseGuardChatModel:
    return FakeAdviseGuardChatModel(**{k: v for k, v in kwargs.items() if k in ("temperature",)})


def fake_embeddings(**kwargs: Any) -> FakeAdviseGuardEmbeddings:
    _ = kwargs
    return FakeAdviseGuardEmbeddings()
