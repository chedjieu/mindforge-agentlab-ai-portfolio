"""Episodic decision memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
EPI = ROOT / "data" / "episodic"


def load_episodic(domain: str, case_id: str | None = None) -> list[dict[str, Any]]:
    path = EPI / f"{domain}.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if case_id and row.get("case_id") not in (case_id, "*"):
            continue
        rows.append(row)
    return rows


def append_episodic(domain: str, event: dict[str, Any]) -> None:
    EPI.mkdir(parents=True, exist_ok=True)
    path = EPI / f"{domain}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, default=str) + "\n")
