"""Thin memory layer accessors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent


def load_procedural_prompt(name: str = "advisor_latest.json") -> dict[str, Any]:
    path = ROOT / "data" / "prompts" / name
    if not path.exists():
        return {"version": "latest", "system": "AdviseGuard default procedural prompt"}
    return json.loads(path.read_text(encoding="utf-8"))


def load_episodic(limit: int = 5) -> list[dict[str, Any]]:
    path = ROOT / "data" / "past_interactions.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows[-limit:]
