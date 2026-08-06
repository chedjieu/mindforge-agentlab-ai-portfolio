"""Append / load HITL outcomes for refine-cron / ops dashboards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_LOG = Path(__file__).resolve().parent.parent / "data" / "hitl_outcomes.jsonl"
LOG_PATH = DEFAULT_LOG


def append_hitl_outcome(row: dict[str, Any], path: Path | None = None) -> None:
    target = path or DEFAULT_LOG
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_hitl_outcomes(path: Path | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Return the last `limit` HITL outcome rows (oldest→newest within the window)."""
    target = path or DEFAULT_LOG
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    with target.open(encoding="utf-8-sig") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    if limit <= 0:
        return rows
    return rows[-limit:]
