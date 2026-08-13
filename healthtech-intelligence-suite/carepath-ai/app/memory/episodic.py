"""Episodic memory — patient encounter history JSONL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PATIENTS = ROOT / "data" / "patients"


def load_episodic(patient_id: str) -> list[dict[str, Any]]:
    path = PATIENTS / patient_id / "history.jsonl"
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            continue
    return rows


def append_episodic(patient_id: str, event: dict[str, Any]) -> None:
    folder = PATIENTS / patient_id
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "history.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")
