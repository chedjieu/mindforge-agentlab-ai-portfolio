"""Publish approved answers to the local audit log."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "published_answers.log"


def publish_answer(
    *,
    thread_id: str,
    domain: str | None,
    query: str,
    answer: str,
    citations: list[dict],
    grounding_score: float | None,
    approval: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one JSON line to data/published_answers.log."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "thread_id": thread_id,
        "domain": domain,
        "query": query,
        "answer": answer,
        "citations": citations,
        "grounding_score": grounding_score,
        "approval": approval,
    }
    if extra:
        row.update(extra)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {"ok": True, "path": str(LOG_PATH)}
