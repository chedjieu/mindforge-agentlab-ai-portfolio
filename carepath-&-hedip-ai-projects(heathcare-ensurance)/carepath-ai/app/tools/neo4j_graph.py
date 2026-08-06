"""Neo4j GraphRAG with JSONL fallback."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
KG_DIR = ROOT / "data" / "kg"


def _load_entities() -> list[dict[str, Any]]:
    path = KG_DIR / "entities.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _load_edges() -> list[dict[str, Any]]:
    path = KG_DIR / "edges.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def graph_lookup(entity_type: str, name: str, limit: int = 5) -> list[dict[str, Any]]:
    uri = os.getenv("NEO4J_URI", "").strip()
    if uri:
        try:
            return _neo4j_lookup(entity_type, name, limit)
        except Exception:
            pass
    return _jsonl_lookup(entity_type, name, limit)


def find_interactions(med_names: list[str], limit: int = 10) -> list[dict[str, Any]]:
    uri = os.getenv("NEO4J_URI", "").strip()
    if uri:
        try:
            return _neo4j_interactions(med_names, limit)
        except Exception:
            pass
    return _jsonl_interactions(med_names, limit)


def guideline_for_condition(condition: str, limit: int = 5) -> list[dict[str, Any]]:
    uri = os.getenv("NEO4J_URI", "").strip()
    if uri:
        try:
            return _neo4j_guidelines(condition, limit)
        except Exception:
            pass
    return _jsonl_guidelines(condition, limit)


def _jsonl_lookup(entity_type: str, name: str, limit: int) -> list[dict[str, Any]]:
    entities = _load_entities()
    edges = _load_edges()
    name_l = (name or "").lower()
    matched = [
        e
        for e in entities
        if (not entity_type or e.get("type", "").lower() == entity_type.lower())
        and name_l in str(e.get("name", "")).lower()
    ]
    ids = {e.get("id") for e in matched}
    related = [
        edge
        for edge in edges
        if edge.get("from") in ids or edge.get("to") in ids or name_l in json.dumps(edge).lower()
    ]
    out = [{"entity": e, "kind": "entity"} for e in matched[:limit]]
    out.extend({"edge": e, "kind": "edge"} for e in related[:limit])
    return out[: limit * 2]


def _jsonl_interactions(med_names: list[str], limit: int) -> list[dict[str, Any]]:
    edges = _load_edges()
    meds = {m.lower() for m in med_names}
    hits = []
    for e in edges:
        if e.get("rel") != "INTERACTS_WITH":
            continue
        a = str(e.get("from_name") or e.get("from") or "").lower()
        b = str(e.get("to_name") or e.get("to") or "").lower()
        if (a in meds and b in meds) or (a in meds or b in meds):
            if a in meds and b in meds:
                hits.append(
                    {
                        "severity": e.get("severity", "moderate"),
                        "pair": [a, b],
                        "note": e.get("note") or "KG interaction",
                        "source": "kg",
                    }
                )
    return hits[:limit]


def _jsonl_guidelines(condition: str, limit: int) -> list[dict[str, Any]]:
    edges = _load_edges()
    entities = {e.get("id"): e for e in _load_entities()}
    cond_l = condition.lower()
    out = []
    for e in edges:
        if e.get("rel") not in ("GUIDELINE_FOR", "MONITORS", "HAS_CONDITION"):
            blob = json.dumps(e).lower()
            if cond_l not in blob:
                continue
        else:
            blob = json.dumps(e).lower()
            if cond_l not in blob and cond_l not in str(e.get("from_name", "")).lower():
                # also match entity names
                fr = entities.get(e.get("from"), {})
                to = entities.get(e.get("to"), {})
                if cond_l not in json.dumps(fr).lower() and cond_l not in json.dumps(to).lower():
                    continue
        out.append({"edge": e, "kind": "guideline_path"})
        if len(out) >= limit:
            break
    return out


def _neo4j_lookup(entity_type: str, name: str, limit: int) -> list[dict[str, Any]]:
    from neo4j import GraphDatabase

    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(user, password))
    cypher = """
    MATCH (n)
    WHERE ($etype = '' OR $etype IN labels(n))
      AND toLower(coalesce(n.name, '')) CONTAINS toLower($name)
    OPTIONAL MATCH (n)-[r]-(m)
    RETURN labels(n) AS labels, properties(n) AS props, type(r) AS rel, properties(m) AS neighbor
    LIMIT $limit
    """
    out: list[dict[str, Any]] = []
    with driver.session() as session:
        for rec in session.run(cypher, etype=entity_type or "", name=name, limit=limit):
            out.append(dict(rec))
    driver.close()
    return out


def _neo4j_interactions(med_names: list[str], limit: int) -> list[dict[str, Any]]:
    from neo4j import GraphDatabase

    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(user, password))
    cypher = """
    MATCH (a:Medication)-[r:INTERACTS_WITH]-(b:Medication)
    WHERE toLower(a.name) IN $meds AND toLower(b.name) IN $meds
    RETURN a.name AS a, b.name AS b, r.severity AS severity, r.note AS note
    LIMIT $limit
    """
    meds = [m.lower() for m in med_names]
    out: list[dict[str, Any]] = []
    with driver.session() as session:
        for rec in session.run(cypher, meds=meds, limit=limit):
            out.append(
                {
                    "severity": rec["severity"] or "moderate",
                    "pair": [rec["a"], rec["b"]],
                    "note": rec["note"] or "Neo4j interaction",
                    "source": "neo4j",
                }
            )
    driver.close()
    return out


def _neo4j_guidelines(condition: str, limit: int) -> list[dict[str, Any]]:
    from neo4j import GraphDatabase

    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    driver = GraphDatabase.driver(os.environ["NEO4J_URI"], auth=(user, password))
    cypher = """
    MATCH (g)-[r:GUIDELINE_FOR]->(c:Condition)
    WHERE toLower(c.name) CONTAINS toLower($cond)
    RETURN properties(g) AS guideline, properties(c) AS condition, type(r) AS rel
    LIMIT $limit
    """
    out: list[dict[str, Any]] = []
    with driver.session() as session:
        for rec in session.run(cypher, cond=condition, limit=limit):
            out.append(dict(rec))
    driver.close()
    return out
