"""Semantic feedback store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "semantic_store.jsonl"


def load_semantic(key: str) -> list[dict[str, Any]]:
    if not STORE.exists():
        return []
    rows = []
    for line in STORE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("key") in (key, "*"):
            rows.append(row)
    return rows


def save_semantic(key: str, payload: dict[str, Any]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    with STORE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"key": key, **payload}, default=str) + "\n")
