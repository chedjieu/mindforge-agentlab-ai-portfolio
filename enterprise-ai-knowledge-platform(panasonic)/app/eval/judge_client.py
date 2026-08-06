"""LLM-as-judge client with cross-provider bias guard."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

from langchain_core.messages import BaseMessage

from app._fake_llm import is_fake_chat_model
from app.llm import DEFAULT_MODEL, get_chat_model


def _provider(model_name: str) -> str:
    name = (model_name or "").strip().lower()
    if is_fake_chat_model(name) or name in {"", "fake"}:
        return "fake"
    if "vertex" in name or name.startswith("google"):
        return "vertex"
    if "bedrock" in name or name.startswith("anthropic") or "gpt-oss" in name:
        return "bedrock"
    if name.startswith("openai") or "gpt-" in name:
        return "openai"
    return name.split(":", 1)[0] if ":" in name else name


def get_answerer_model_name() -> str:
    return (os.getenv("EGKP_MODEL") or DEFAULT_MODEL).strip()


def get_judge_model_name() -> str:
    explicit = (os.getenv("EGKP_JUDGE_MODEL") or "").strip()
    if explicit:
        return explicit
    answerer = get_answerer_model_name()
    if is_fake_chat_model(answerer):
        return "fake"
    if _provider(answerer) == "bedrock":
        return "google_vertexai:gemini-2.5-pro"
    if _provider(answerer) == "vertex":
        return DEFAULT_MODEL
    return "fake"


def assert_cross_provider() -> None:
    answerer = get_answerer_model_name()
    judge = get_judge_model_name()
    if is_fake_chat_model(answerer) or is_fake_chat_model(judge):
        return
    if _provider(answerer) == _provider(judge):
        raise RuntimeError(
            "same-model bias: configure EGKP_JUDGE_MODEL on the other cloud"
        )


def get_judge_model(**kwargs: Any):
    assert_cross_provider()
    return get_chat_model(get_judge_model_name(), **kwargs)


def judge_chat(messages: list[BaseMessage], timeout_s: float | None = None) -> str | None:
    """Invoke judge model; return text or None on failure/timeout (fail-closed)."""
    timeout_s = float(timeout_s or os.getenv("EGKP_JUDGE_TIMEOUT", "45"))

    def _invoke() -> str:
        model = get_judge_model()
        msg = model.invoke(messages)
        content = msg.content
        return content if isinstance(content, str) else str(content)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_invoke)
            return fut.result(timeout=timeout_s)
    except (FuturesTimeout, Exception):
        return None


__all__ = [
    "assert_cross_provider",
    "get_answerer_model_name",
    "get_judge_model",
    "get_judge_model_name",
    "judge_chat",
]
