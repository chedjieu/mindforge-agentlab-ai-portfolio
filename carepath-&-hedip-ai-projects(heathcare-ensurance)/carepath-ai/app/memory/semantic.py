"""Semantic memory — clinician corrections / plan feedback store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data" / "semantic_store.jsonl"


def load_semantic_feedback(patient_id: str) -> list[dict[str, Any]]:
    if not STORE.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in STORE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if row.get("patient_id") in (patient_id, "*", None):
            rows.append(row)
    return rows


def save_semantic_feedback(patient_id: str, payload: dict[str, Any]) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    row = {"patient_id": patient_id, **payload}
    with STORE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")
