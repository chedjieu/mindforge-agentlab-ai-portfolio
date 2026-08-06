"""Neo4j GraphRAG with JSONL fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
KG_DIR = ROOT / "data" / "kg"


def _load_jsonl() -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    if not KG_DIR.exists():
        return edges
    for path in KG_DIR.glob("*.jsonl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            edges.append(json.loads(line))
    return edges


def graph_hops(associate_id: str, intent_hints: list[str] | None = None, limit: int = 8) -> list[dict[str, Any]]:
    """Return multi-hop relationship facts for an associate."""
    uri = os.getenv("NEO4J_URI", "").strip()
    if uri:
        try:
            return _neo4j_hops(associate_id, intent_hints, limit)
        except Exception:
            pass
    return _jsonl_hops(associate_id, intent_hints, limit)


def _jsonl_hops(associate_id: str, intent_hints: list[str] | None, limit: int) -> list[dict[str, Any]]:
    edges = _load_jsonl()
    hints = {h.lower() for h in (intent_hints or [])}
    related = [
        e
        for e in edges
        if e.get("associate_id") in (associate_id, "*")
        or not e.get("associate_id")
        or (hints and any(h in json.dumps(e).lower() for h in hints))
    ]
    # prefer associate-specific
    related.sort(key=lambda e: 0 if e.get("associate_id") == associate_id else 1)
    return related[:limit]


def _neo4j_hops(associate_id: str, intent_hints: list[str] | None, limit: int) -> list[dict[str, Any]]:
    from neo4j import GraphDatabase  # optional dependency

    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(user, password))
    cypher = """
    MATCH (a:Associate {id: $aid})-[r]->(n)
    OPTIONAL MATCH (n)-[r2]->(m)
    RETURN type(r) AS rel, labels(n) AS labels, properties(n) AS props,
           type(r2) AS rel2, labels(m) AS labels2, properties(m) AS props2
    LIMIT $limit
    """
    out: list[dict[str, Any]] = []
    with driver.session() as session:
        for rec in session.run(cypher, aid=associate_id, limit=limit):
            out.append(dict(rec))
    driver.close()
    return out
