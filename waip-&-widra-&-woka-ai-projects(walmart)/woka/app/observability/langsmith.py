"""Optional LangSmith / LangChain tracing bootstrap."""

from __future__ import annotations

import os
from typing import Any


def configure_langsmith() -> dict[str, Any]:
    """Enable tracing env vars when an API key is present. Safe no-op otherwise."""
    key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY") or ""
    project = (
        os.getenv("LANGSMITH_PROJECT")
        or os.getenv("LANGCHAIN_PROJECT")
        or "woka"
    )
    enabled = bool(key)
    if enabled:
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGCHAIN_PROJECT", project)
        os.environ.setdefault("LANGSMITH_PROJECT", project)
        if os.getenv("LANGSMITH_API_KEY") and not os.getenv("LANGCHAIN_API_KEY"):
            os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]
        if os.getenv("LANGCHAIN_API_KEY") and not os.getenv("LANGSMITH_API_KEY"):
            os.environ["LANGSMITH_API_KEY"] = os.environ["LANGCHAIN_API_KEY"]
    return {
        "enabled": enabled,
        "project": project,
        "tracing": (os.getenv("LANGCHAIN_TRACING_V2") or "").lower() in {"1", "true", "yes"},
    }


def langsmith_meta() -> dict[str, Any]:
    return configure_langsmith()
