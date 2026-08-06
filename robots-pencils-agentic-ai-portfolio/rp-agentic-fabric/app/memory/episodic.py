"""Episodic memory — similar past engagements (JSONL fallback)."""

from __future__ import annotations

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "verticals"


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9\-]+", (text or "").lower()) if len(t) > 2}


def recall_similar_engagements(tenant_id: str, vertical: str, query: str, k: int = 3) -> list[dict]:
    path = DATA_DIR / vertical / "historical_engagements.jsonl"
    if not path.exists():
        return []
    qtoks = _tokenize(query)
    scored = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("tenant_id") not in (tenant_id, "shared"):
            continue
        overlap = len(qtoks & _tokenize(json.dumps(row)))
        scored.append((overlap, row))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in scored[:k]]
