"""Chat / embeddings factory for RoboForge."""

from __future__ import annotations

import os
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypeVar

from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings

from app._fake_llm import (
    FakeRFAIChatModel,
    FakeRFAIEmbeddings,
    fake_chat_model,
    fake_embeddings,
    is_fake_chat_model,
    is_fake_embeddings,
)

DEFAULT_MODEL = "bedrock_converse:openai.gpt-oss-120b-1:0"
DEFAULT_EMBEDDINGS = "bedrock:amazon.titan-embed-text-v2:0"
T = TypeVar("T")


def is_throttling_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "throttl" in msg or "too many tokens" in msg


def activate_fake_fallback() -> None:
    os.environ["RFAI_MODEL"] = "fake"
    os.environ["RFAI_EMBEDDINGS"] = "fake"
    get_chat_model.cache_clear()
    get_embeddings.cache_clear()


def invoke_with_throttle_fallback(fn: Callable[[], T]) -> T:
    try:
        return fn()
    except Exception as exc:
        if is_throttling_error(exc) and os.getenv("RFAI_ALLOW_FAKE_FALLBACK", "1") != "0":
            activate_fake_fallback()
            return fn()
        raise


@lru_cache(maxsize=4)
def get_chat_model(name: str | None = None, **kwargs: Any):
    resolved = (name or os.getenv("RFAI_MODEL") or DEFAULT_MODEL).strip()
    if is_fake_chat_model(resolved):
        return fake_chat_model(**kwargs)
    model_kwargs = dict(kwargs)
    if "google_vertexai" in resolved:
        project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GCP_LOCATION") or "us-central1"
        if project:
            model_kwargs.setdefault("project", project)
        model_kwargs.setdefault("location", location)
    return init_chat_model(resolved, **model_kwargs)


@lru_cache(maxsize=4)
def get_embeddings(name: str | None = None, **kwargs: Any):
    resolved = (name or os.getenv("RFAI_EMBEDDINGS") or DEFAULT_EMBEDDINGS).strip()
    if is_fake_embeddings(resolved):
        return fake_embeddings(**kwargs)
    return init_embeddings(resolved, **kwargs)


__all__ = [
    "FakeRFAIChatModel",
    "FakeRFAIEmbeddings",
    "get_chat_model",
    "get_embeddings",
    "invoke_with_throttle_fallback",
]
