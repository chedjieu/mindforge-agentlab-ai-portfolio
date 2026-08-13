"""Model gateway: Bedrock, Vertex, or fake."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

from app._fake_llm import FakeChatModel, FakeEmbeddings, is_fake_chat_model, is_fake_embeddings
from app.config import get_settings

load_dotenv()
logger = logging.getLogger(__name__)

DEFAULT_MODEL = "bedrock_converse:anthropic.claude-3-5-sonnet-20241022-v2:0"
DEFAULT_JUDGE = "google_vertexai:gemini-2.5-pro"


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
    logger.warning("RAIP falling back to fake model (%s)", reason)
    os.environ["RAIP_MODEL"] = "fake"
    os.environ["RAIP_EMBEDDINGS"] = "fake"
    os.environ["RAIP_JUDGE_MODEL"] = "fake"
    reset_llm_cache()


def _init_chat(name: str) -> Any:
    if is_fake_chat_model(name):
        return FakeChatModel()
    try:
        from langchain.chat_models import init_chat_model
    except Exception:
        from langchain_core.language_models import init_chat_model  # type: ignore[no-redef]

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
    name = os.getenv("RAIP_MODEL", get_settings().model).strip()
    try:
        return _init_chat(name)
    except Exception as exc:  # noqa: BLE001
        if _is_throttle(exc):
            _fallback_to_fake(str(exc))
            return FakeChatModel()
        logger.warning("Chat model unavailable (%s); using fake", exc)
        return FakeChatModel()


@lru_cache(maxsize=4)
def get_judge_model() -> Any:
    configured = os.getenv("RAIP_JUDGE_MODEL", get_settings().judge_model).strip()
    worker = os.getenv("RAIP_MODEL", get_settings().model).strip()
    name = configured or _cross_provider_judge(worker)
    try:
        return _init_chat(name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Judge model unavailable (%s); using fake", exc)
        return FakeChatModel()


@lru_cache(maxsize=4)
def get_embeddings() -> Any:
    name = os.getenv("RAIP_EMBEDDINGS", get_settings().embeddings).strip()
    if is_fake_embeddings(name) or is_fake_chat_model(os.getenv("RAIP_MODEL", "fake")):
        return FakeEmbeddings(dim=get_settings().embed_dim)
    try:
        from langchain.embeddings import init_embeddings
    except Exception:
        from langchain_core.embeddings import init_embeddings  # type: ignore[no-redef]
    try:
        return init_embeddings(name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Embeddings unavailable (%s); using fake", exc)
        return FakeEmbeddings(dim=get_settings().embed_dim)


def reset_llm_cache() -> None:
    get_chat_model.cache_clear()
    get_judge_model.cache_clear()
    get_embeddings.cache_clear()


def invoke_text(model: Any, prompt: str) -> str:
    msg = model.invoke(prompt)
    content = getattr(msg, "content", msg)
    if isinstance(content, list):
        return "".join(str(part) for part in content)
    return str(content)
