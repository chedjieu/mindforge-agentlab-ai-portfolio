"""Model gateway: Bedrock, Vertex, or fake — with Bedrock throttle fallback."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv

from app._fake_llm import FakeChatModel, FakeEmbeddings

load_dotenv()

logger = logging.getLogger(__name__)


def _model_name() -> str:
    return os.getenv("WIDRA_MODEL", "fake").strip()


def _embeddings_name() -> str:
    return os.getenv("WIDRA_EMBEDDINGS", "fake").strip()


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
    logger.warning("WIDRA falling back to fake model/embeddings (%s)", reason)
    os.environ["WIDRA_MODEL"] = "fake"
    os.environ["WIDRA_EMBEDDINGS"] = "fake"
    reset_llm_cache()


@lru_cache(maxsize=4)
def get_chat_model() -> Any:
    name = _model_name()
    if name == "fake" or name.startswith("fake"):
        return FakeChatModel()

    try:
        from langchain.chat_models import init_chat_model
    except Exception:
        from langchain_core.language_models import init_chat_model  # type: ignore

    try:
        return init_chat_model(name)
    except Exception as exc:  # noqa: BLE001
        if _is_throttle(exc):
            _fallback_to_fake(str(exc))
            return FakeChatModel()
        raise


@lru_cache(maxsize=4)
def get_embeddings() -> Any:
    emb = _embeddings_name()
    if emb == "fake" or _model_name() == "fake":
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
    get_embeddings.cache_clear()
