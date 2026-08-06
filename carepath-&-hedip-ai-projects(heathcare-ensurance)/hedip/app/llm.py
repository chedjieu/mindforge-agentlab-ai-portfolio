"""Model gateway: Bedrock, Vertex, or fake."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

from app._fake_llm import FakeChatModel, FakeEmbeddings, is_fake

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "bedrock_converse:anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_JUDGE = "google_vertexai:gemini-2.5-pro"


def _model_name() -> str:
    return os.getenv("HEDIP_MODEL", "fake").strip()


def _judge_name() -> str:
    explicit = os.getenv("HEDIP_JUDGE_MODEL", "").strip()
    if explicit:
        return explicit
    worker = _model_name()
    if is_fake(worker):
        return "fake"
    if "bedrock" in worker:
        return DEFAULT_JUDGE
    return DEFAULT_MODEL


def _embeddings_name() -> str:
    return os.getenv("HEDIP_EMBEDDINGS", "fake").strip()


def _is_throttle(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(t in text for t in ("throttl", "too many tokens", "rate exceeded", "too many requests"))


def _fallback(reason: str) -> None:
    logger.warning("HEDIP falling back to fake (%s)", reason)
    os.environ["HEDIP_MODEL"] = "fake"
    os.environ["HEDIP_EMBEDDINGS"] = "fake"
    os.environ["HEDIP_JUDGE_MODEL"] = "fake"
    reset_llm_cache()


def _init_chat(name: str) -> Any:
    if is_fake(name):
        return FakeChatModel()
    try:
        from langchain.chat_models import init_chat_model
    except Exception:
        from langchain_core.language_models import init_chat_model  # type: ignore
    kwargs: dict[str, Any] = {}
    if "google_vertexai" in name or name.startswith("vertexai"):
        project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GCP_LOCATION") or os.getenv("GOOGLE_CLOUD_LOCATION") or "us-central1"
        if project:
            kwargs["project"] = project
        if location:
            kwargs["location"] = location
    return init_chat_model(name, **kwargs)


@lru_cache(maxsize=4)
def get_chat_model() -> Any:
    try:
        return _init_chat(_model_name())
    except Exception as exc:  # noqa: BLE001
        if _is_throttle(exc):
            _fallback(str(exc))
            return FakeChatModel()
        raise


@lru_cache(maxsize=4)
def get_judge_model() -> Any:
    try:
        return _init_chat(_judge_name())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Judge unavailable (%s); using fake", exc)
        return FakeChatModel()


@lru_cache(maxsize=4)
def get_embeddings() -> Any:
    if is_fake(_embeddings_name()) or is_fake(_model_name()):
        return FakeEmbeddings()
    try:
        from langchain.embeddings import init_embeddings
    except Exception:
        from langchain_core.embeddings import init_embeddings  # type: ignore
    try:
        return init_embeddings(_embeddings_name())
    except Exception as exc:  # noqa: BLE001
        if _is_throttle(exc):
            _fallback(str(exc))
            return FakeEmbeddings()
        raise


def reset_llm_cache() -> None:
    get_chat_model.cache_clear()
    get_judge_model.cache_clear()
    get_embeddings.cache_clear()
