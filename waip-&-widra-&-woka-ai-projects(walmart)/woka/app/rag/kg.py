"""GraphRAG hops over supply-chain KG (JSONL/JSON fallback; Neo4j optional)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
KG_PATH = ROOT / "data" / "kg" / "supply_chain.json"


def _load_kg() -> dict[str, Any]:
    if not KG_PATH.exists():
        return {"entities": [], "edges": []}
    return json.loads(KG_PATH.read_text(encoding="utf-8"))


def graph_hops(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Return multi-hop facts relevant to the query tokens."""
    uri = os.getenv("NEO4J_URI", "").strip()
    if uri:
        try:
            hops = _neo4j_hops(query, limit)
            if hops:
                return hops
        except Exception:
            pass
    return _json_hops(query, limit)


def _json_hops(query: str, limit: int) -> list[dict[str, Any]]:
    kg = _load_kg()
    entities = {e["id"]: e for e in kg.get("entities", []) if "id" in e}
    edges = kg.get("edges", [])
    tokens = set(re.findall(r"[a-z0-9\-]+", query.lower()))
    # Expand entity ids mentioned
    mentioned = {
        eid
        for eid, ent in entities.items()
        if eid.lower() in query.upper().replace(" ", "-")
        or any(t in json.dumps(ent).lower() for t in tokens if len(t) > 2)
    }
    # Always include closed DCs for hurricane / disruption queries
    if tokens & {"hurricane", "disruption", "closed", "southeast", "stockout", "supplier"}:
        for eid, ent in entities.items():
            if ent.get("type") == "DC" and ent.get("status") == "closed":
                mentioned.add(eid)
            if ent.get("type") in {"Supplier", "Contract", "SKU", "Store"}:
                mentioned.add(eid)

    facts: list[dict[str, Any]] = []
    for e in edges:
        frm, to, rel = e.get("from"), e.get("to"), e.get("rel")
        if frm in mentioned or to in mentioned:
            facts.append(
                {
                    "from": frm,
                    "rel": rel,
                    "to": to,
                    "from_entity": entities.get(frm, {}),
                    "to_entity": entities.get(to, {}),
                    "source": "kg:supply_chain",
                }
            )
    # Prefer alt-sourcing and closed-DC facts
    facts.sort(
        key=lambda f: (
            0 if f.get("rel") in {"BACKUP_FOR", "COVERS", "SUPPLIES"} else 1,
            0 if (f.get("from_entity") or {}).get("status") == "closed" else 1,
        )
    )
    return facts[:limit]


def _neo4j_hops(query: str, limit: int) -> list[dict[str, Any]]:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password")),
    )
    cypher = """
    MATCH (a)-[r]->(b)
    RETURN labels(a) AS from_labels, properties(a) AS from_props,
           type(r) AS rel, labels(b) AS to_labels, properties(b) AS to_props
    LIMIT $limit
    """
    out: list[dict[str, Any]] = []
    with driver.session() as session:
        for rec in session.run(cypher, limit=limit):
            out.append(dict(rec))
    driver.close()
    return out
