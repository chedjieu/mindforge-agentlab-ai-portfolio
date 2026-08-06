"""Procedural memory — versioned treatment protocols from disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROTOCOLS = ROOT / "data" / "protocols"


def load_all_protocols() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not PROTOCOLS.exists():
        return out
    for path in sorted(PROTOCOLS.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                out.extend(data)
            else:
                out.append(data)
        except Exception:
            continue
    return out


def load_protocols_for_conditions(conditions: list[str]) -> list[dict[str, Any]]:
    all_p = load_all_protocols()
    if not conditions:
        return all_p[:3]
    low = " ".join(conditions).lower()
    matched = []
    for p in all_p:
        tags = " ".join(
            [
                str(p.get("id") or ""),
                str(p.get("name") or ""),
                str(p.get("title") or ""),
                " ".join(p.get("conditions") or []),
                " ".join(p.get("tags") or []),
            ]
        ).lower()
        if any(tok in tags or tok in low for tok in tags.split() if len(tok) > 3):
            # better: condition token overlap
            matched.append(p)
            continue
        for cond in conditions:
            c = cond.lower()
            if any(word in tags for word in c.split() if len(word) > 3):
                matched.append(p)
                break
    # de-dupe
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for p in matched or all_p[:3]:
        key = str(p.get("id") or p.get("name") or id(p))
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq
