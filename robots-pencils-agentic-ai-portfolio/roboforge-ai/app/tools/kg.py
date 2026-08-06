"""KG tools — JSONL fallback."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

KG = Path(__file__).resolve().parent.parent.parent / "data" / "kg"


@lru_cache(maxsize=1)
def _entities() -> list[dict]:
    path = KG / "seed_entities.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


@lru_cache(maxsize=1)
def _relations() -> list[dict]:
    path = KG / "seed_relations.jsonl"
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def lookup_entity(query: str, client_id: str, domain: str) -> dict | None:
    q = (query or "").lower()
    for e in _entities():
        if e.get("client_id") not in (client_id, "shared", None) and not e.get("reusable"):
            continue
        blob = f"{e.get('name','')} {e.get('id','')} {e.get('label','')}".lower()
        if domain in blob or any(t in blob for t in q.split()[:5] if len(t) > 3):
            return dict(e)
    for e in _entities():
        if e.get("domain") == domain:
            return dict(e)
    return {
        "id": f"app-{domain}",
        "name": f"{domain} target application",
        "label": "Application",
        "client_id": client_id,
        "domain": domain,
    }


def traverse_relations(entity_id: str | None, client_id: str) -> list[dict]:
    if not entity_id:
        return []
    out = []
    for r in _relations():
        if r.get("source") == entity_id or r.get("target") == entity_id:
            out.append(r)
    return out[:10]
