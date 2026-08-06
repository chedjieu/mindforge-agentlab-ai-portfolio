"""Neo4j GraphRAG with JSONL fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
KG = ROOT / "data" / "kg"


def _load(name: str) -> list[dict[str, Any]]:
    path = KG / name
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def graph_lookup(query: str, limit: int = 8) -> list[dict[str, Any]]:
    uri = os.getenv("NEO4J_URI", "").strip()
    if uri:
        try:
            return _neo4j(query, limit)
        except Exception:
            pass
    q = (query or "").lower()
    entities = _load("entities.jsonl")
    edges = _load("edges.jsonl")
    hits = [e for e in entities if q in json.dumps(e).lower()]
    ehits = [e for e in edges if q in json.dumps(e).lower()]
    out = [{"kind": "entity", **e} for e in hits[:limit]]
    out.extend({"kind": "edge", **e} for e in ehits[:limit])
    return out[:limit]


def graph_hops(seed: str, rel: str | None = None, limit: int = 8) -> list[dict[str, Any]]:
    edges = _load("edges.jsonl")
    seed_l = seed.lower()
    out = []
    for e in edges:
        blob = json.dumps(e).lower()
        if seed_l not in blob:
            continue
        if rel and e.get("rel") != rel:
            continue
        out.append(e)
        if len(out) >= limit:
            break
    return out


def _neo4j(query: str, limit: int) -> list[dict[str, Any]]:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password")),
    )
    cypher = """
    MATCH (n)
    WHERE toLower(coalesce(n.name,'')) CONTAINS toLower($q)
       OR toLower(coalesce(n.id,'')) CONTAINS toLower($q)
    OPTIONAL MATCH (n)-[r]-(m)
    RETURN labels(n) AS labels, properties(n) AS props, type(r) AS rel, properties(m) AS neighbor
    LIMIT $limit
    """
    out = []
    with driver.session() as session:
        for rec in session.run(cypher, q=query, limit=limit):
            out.append(dict(rec))
    driver.close()
    return out
