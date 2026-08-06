"""Provider-agnostic chat-model and embeddings factory."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from functools import lru_cache
from typing import Any, TypeVar

from langchain.chat_models import init_chat_model
from langchain.embeddings import init_embeddings
from langchain_core.messages import HumanMessage

from app._fake_llm import (
    FakeAdviseGuardChatModel,
    FakeAdviseGuardEmbeddings,
    fake_chat_model,
    fake_embeddings,
    is_fake_chat_model,
    is_fake_embeddings,
)

logger = logging.getLogger(__name__)
DEFAULT_MODEL = "bedrock_converse:anthropic.claude-sonnet-4-20250514-v1:0"
DEFAULT_EMBEDDINGS = "bedrock:amazon.titan-embed-text-v2:0"
T = TypeVar("T")
_fallback_logged = False


def is_throttling_error(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    return "throttl" in name or "throttl" in msg or "too many tokens" in msg


def activate_fake_fallback() -> None:
    global _fallback_logged
    os.environ["ADVISEGUARD_MODEL"] = "fake"
    os.environ["ADVISEGUARD_EMBEDDINGS"] = "fake"
    get_chat_model.cache_clear()
    get_embeddings.cache_clear()
    if not _fallback_logged:
        logger.warning("Cloud model throttled — switched to ADVISEGUARD_MODEL=fake.")
        _fallback_logged = True


def invoke_with_throttle_fallback(fn: Callable[[], T]) -> T:
    try:
        return fn()
    except Exception as exc:
        deny = os.getenv("ADVISEGUARD_ALLOW_FAKE_FALLBACK", "1").strip().lower() in (
            "0",
            "false",
            "no",
        )
        if is_throttling_error(exc) and not deny:
            activate_fake_fallback()
            return fn()
        raise


def _resolved_chat_name(name: str | None) -> str:
    return (name or os.getenv("ADVISEGUARD_MODEL") or DEFAULT_MODEL).strip()


def _resolved_embedding_name(name: str | None) -> str:
    return (name or os.getenv("ADVISEGUARD_EMBEDDINGS") or DEFAULT_EMBEDDINGS).strip()


@lru_cache(maxsize=4)
def get_chat_model(name: str | None = None, **kwargs: Any):
    resolved = _resolved_chat_name(name)
    if is_fake_chat_model(resolved):
        return fake_chat_model(**kwargs)
    model_kwargs = dict(kwargs)
    if "google_vertexai" in resolved or resolved.startswith("vertexai"):
        project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GCP_LOCATION") or "us-central1"
        if project:
            model_kwargs.setdefault("project", project)
        model_kwargs.setdefault("location", location)
    return init_chat_model(resolved, **model_kwargs)


@lru_cache(maxsize=4)
def get_embeddings(name: str | None = None, **kwargs: Any):
    resolved = _resolved_embedding_name(name)
    if is_fake_embeddings(resolved):
        return fake_embeddings(**kwargs)
    return init_embeddings(resolved, **kwargs)


def ensure_chat_model_available() -> bool:
    if is_fake_chat_model(_resolved_chat_name(None)):
        return True
    get_chat_model().invoke([HumanMessage(content="Reply with exactly: ok")])
    return False


__all__ = [
    "DEFAULT_EMBEDDINGS",
    "DEFAULT_MODEL",
    "FakeAdviseGuardChatModel",
    "FakeAdviseGuardEmbeddings",
    "activate_fake_fallback",
    "ensure_chat_model_available",
    "get_chat_model",
    "get_embeddings",
    "invoke_with_throttle_fallback",
    "is_throttling_error",
    "_resolved_chat_name",
]
