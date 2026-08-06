"""Episodic memory — past lessons."""

from __future__ import annotations

import json
import re
from pathlib import Path

EPISODIC = Path(__file__).resolve().parent.parent.parent / "data" / "episodic"
LESSONS = EPISODIC / "lessons.jsonl"


def _tok(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9\-]+", (text or "").lower()) if len(t) > 2}


def recall_similar(client_id: str, domain: str, query: str, k: int = 3) -> list[dict]:
    if not LESSONS.exists():
        return []
    q = _tok(query)
    scored = []
    for line in LESSONS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("domain") not in (domain, "shared") and row.get("client_id") != client_id:
            continue
        overlap = len(q & _tok(json.dumps(row)))
        scored.append((overlap, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:k]]


def append_lesson(row: dict) -> None:
    LESSONS.parent.mkdir(parents=True, exist_ok=True)
    with LESSONS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
