"""HITL outcome logging."""

from __future__ import annotations

import json
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "data" / "hitl_outcomes.jsonl"


def append_hitl_outcome(row: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
