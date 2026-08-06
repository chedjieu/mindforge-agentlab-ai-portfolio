from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import requests

from app.config import get_settings
from app.memory.long_term import remember
from app.observability.tracing import traced_span
from app.rag.retriever import format_context, retrieve


def search_pdf(question: str, top_k: int = 4) -> str:
    with traced_span("tool.search_pdf"):
        chunks = retrieve(question, top_k=top_k)
        if not chunks:
            return "No indexed documents found. Ingest a PDF first."
        return format_context(chunks)


def get_cardiff_weather() -> str:
    with traced_span("tool.get_cardiff_weather"):
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=51.4816"
            "&longitude=-3.1791"
            "&current=temperature_2m,wind_speed_10m"
        )
        data = requests.get(url, timeout=20).json()
        current = data["current"]
        return (
            f"Temperature: {current['temperature_2m']}°C\n"
            f"Wind Speed: {current['wind_speed_10m']} km/h"
        )


def write_study_note(content: str) -> str:
    with traced_span("tool.write_study_note"):
        settings = get_settings()
        path: Path = settings.study_note_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Saved to {path.resolve()}"


def remember_fact(content: str) -> str:
    with traced_span("tool.remember_fact"):
        mem_id = remember(content)
        return f"Stored long-term memory {mem_id}"


TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "search_pdf": search_pdf,
    "get_cardiff_weather": get_cardiff_weather,
    "write_study_note": write_study_note,
    "remember_fact": remember_fact,
}


def run_tool(name: str, args: dict[str, Any] | None = None) -> str:
    if name not in TOOL_REGISTRY:
        return f"Unknown tool: {name}"
    args = args or {}
    fn = TOOL_REGISTRY[name]
    try:
        return str(fn(**args))
    except TypeError:
        # Retry common zero-arg tools when model sends extra keys
        if name in {"get_cardiff_weather"}:
            return str(fn())
        raise
