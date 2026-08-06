"""Model gateway: Bedrock, Vertex, or fake — with Bedrock throttle fallback."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

from app._fake_llm import FakeChatModel, FakeEmbeddings, is_fake_chat_model, is_fake_embeddings

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "bedrock_converse:anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_JUDGE = "google_vertexai:gemini-2.5-pro"
DEFAULT_EMBEDDINGS = "bedrock:amazon.titan-embed-text-v2:0"


def _model_name() -> str:
    return os.getenv("CAREPATH_MODEL", "fake").strip()


def _judge_name() -> str:
    return os.getenv("CAREPATH_JUDGE_MODEL", "").strip() or _cross_provider_judge(_model_name())


def _embeddings_name() -> str:
    return os.getenv("CAREPATH_EMBEDDINGS", "fake").strip()


def _cross_provider_judge(worker: str) -> str:
    if is_fake_chat_model(worker):
        return "fake"
    if "bedrock" in worker:
        return DEFAULT_JUDGE
    if "vertex" in worker or "google" in worker:
        return DEFAULT_MODEL
    return DEFAULT_JUDGE


def _is_throttle(exc: BaseException) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return any(
        token in text
        for token in (
            "throttlingexception",
            "too many tokens",
            "rate exceeded",
            "too many requests",
            "servicequotaexceeded",
            "provisionedthroughputexceeded",
        )
    )


def _fallback_to_fake(reason: str) -> None:
    logger.warning("CarePath falling back to fake model/embeddings (%s)", reason)
    os.environ["CAREPATH_MODEL"] = "fake"
    os.environ["CAREPATH_EMBEDDINGS"] = "fake"
    os.environ["CAREPATH_JUDGE_MODEL"] = "fake"
    reset_llm_cache()


def _init_chat(name: str) -> Any:
    if is_fake_chat_model(name):
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
    name = _model_name()
    try:
        return _init_chat(name)
    except Exception as exc:  # noqa: BLE001
        if _is_throttle(exc):
            _fallback_to_fake(str(exc))
            return FakeChatModel()
        raise


@lru_cache(maxsize=4)
def get_judge_model() -> Any:
    name = _judge_name()
    try:
        return _init_chat(name)
    except Exception as exc:  # noqa: BLE001
        if _is_throttle(exc):
            _fallback_to_fake(str(exc))
            return FakeChatModel()
        # Prefer fake judge over blocking offline demos
        logger.warning("Judge model unavailable (%s); using fake", exc)
        return FakeChatModel()


@lru_cache(maxsize=4)
def get_embeddings() -> Any:
    emb = _embeddings_name()
    if is_fake_embeddings(emb) or is_fake_chat_model(_model_name()):
        return FakeEmbeddings()
    try:
        from langchain.embeddings import init_embeddings
    except Exception:
        from langchain_core.embeddings import init_embeddings  # type: ignore

    try:
        return init_embeddings(emb)
    except Exception as exc:  # noqa: BLE001
        if _is_throttle(exc):
            _fallback_to_fake(str(exc))
            return FakeEmbeddings()
        raise


def reset_llm_cache() -> None:
    get_chat_model.cache_clear()
    get_judge_model.cache_clear()
    get_embeddings.cache_clear()
