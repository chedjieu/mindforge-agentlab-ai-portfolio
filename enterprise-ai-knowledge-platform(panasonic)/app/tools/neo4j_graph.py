"""Neo4j graph tools with in-process JSONL fallback when Neo4j is unavailable."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

ROOT = Path(__file__).resolve().parent.parent.parent
KG_DIR = ROOT / "data" / "kg"


@lru_cache(maxsize=1)
def _load_seed_graph() -> tuple[dict[str, dict], list[dict]]:
    ent_path = KG_DIR / "seed_entities.jsonl"
    rel_path = KG_DIR / "seed_relations.jsonl"
    entities: dict[str, dict] = {}
    if ent_path.exists():
        for line in ent_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            entities[str(row["id"])] = row
    relations: list[dict] = []
    if rel_path.exists():
        for line in rel_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            relations.append(json.loads(line))
    return entities, relations


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _lookup_seed(name_or_id: str) -> dict | None:
    entities, _ = _load_seed_graph()
    key = (name_or_id or "").strip()
    if not key:
        return None
    if key in entities:
        return dict(entities[key])
    key_l = _normalize(key)
    for ent in entities.values():
        if _normalize(str(ent.get("id", ""))) == key_l:
            return dict(ent)
        if _normalize(str(ent.get("name", ""))) == key_l:
            return dict(ent)
        # loose contains match on id/name
        if key_l in _normalize(str(ent.get("id", ""))) or key_l in _normalize(
            str(ent.get("name", ""))
        ):
            return dict(ent)
    return None


def _traverse_seed(
    entity_id: str,
    rel_types: list[str] | None = None,
    hops: int = 2,
) -> list[dict]:
    entities, relations = _load_seed_graph()
    start = _lookup_seed(entity_id)
    if not start:
        return []
    start_id = str(start["id"])
    allowed = {r.upper() for r in rel_types} if rel_types else None
    hops = max(1, min(int(hops), 3))

    paths: list[dict] = []
    # BFS frontier: (node_id, nodes_so_far, rels_so_far)
    frontier: list[tuple[str, list[str], list[str]]] = [(start_id, [start_id], [])]
    seen_edges: set[tuple[str, str, str]] = set()

    for _ in range(hops):
        next_frontier: list[tuple[str, list[str], list[str]]] = []
        for node_id, nodes, rels in frontier:
            for edge in relations:
                src, dst, rel = str(edge["src"]), str(edge["dst"]), str(edge["rel"]).upper()
                if allowed is not None and rel not in allowed:
                    continue
                nxt: str | None = None
                if src == node_id:
                    nxt = dst
                elif dst == node_id:
                    nxt = src
                if nxt is None:
                    continue
                edge_key = (src, rel, dst)
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                new_nodes = nodes + [nxt]
                new_rels = rels + [rel]
                paths.append(
                    {
                        "nodes": new_nodes,
                        "rels": new_rels,
                        "rationale": f"{' -'.join(new_rels)} from {start_id}",
                        "source": "seed_jsonl",
                    }
                )
                next_frontier.append((nxt, new_nodes, new_rels))
        frontier = next_frontier
        if not frontier:
            break
    return paths


def _neo4j_driver():
    uri = os.getenv("EGKP_NEO4J_URI", "").strip()
    if not uri:
        return None
    from neo4j import GraphDatabase

    user = os.getenv("EGKP_NEO4J_USER", "neo4j")
    password = os.getenv("EGKP_NEO4J_PASSWORD", "password")
    return GraphDatabase.driver(uri, auth=(user, password))


def _lookup_neo4j(name_or_id: str) -> dict | None:
    driver = _neo4j_driver()
    if driver is None:
        return None
    try:
        with driver.session() as session:
            rec = session.run(
                """
                MATCH (n)
                WHERE n.id = $q OR toLower(n.name) = toLower($q)
                   OR toLower(n.id) CONTAINS toLower($q)
                   OR toLower(coalesce(n.name,'')) CONTAINS toLower($q)
                RETURN n.id AS id, n.label AS label, n.name AS name, properties(n) AS props
                LIMIT 1
                """,
                q=name_or_id,
            ).single()
            if not rec:
                return None
            props = dict(rec["props"] or {})
            props.pop("id", None)
            props.pop("name", None)
            props.pop("label", None)
            return {
                "id": rec["id"],
                "label": rec["label"],
                "name": rec["name"],
                "props": props,
                "source": "neo4j",
            }
    except Exception:
        return None
    finally:
        driver.close()


def _traverse_neo4j(
    entity_id: str,
    rel_types: list[str] | None = None,
    hops: int = 2,
) -> list[dict] | None:
    driver = _neo4j_driver()
    if driver is None:
        return None
    hops = max(1, min(int(hops), 3))
    try:
        with driver.session() as session:
            if rel_types:
                # Dynamic rel type filter via string match on type(r)
                cypher = f"""
                MATCH p = (a {{id: $id}})-[*1..{hops}]-(b)
                WHERE ALL(r IN relationships(p) WHERE type(r) IN $rels)
                RETURN [n IN nodes(p) | n.id] AS nodes,
                       [r IN relationships(p) | type(r)] AS rels
                LIMIT 40
                """
                result = session.run(
                    cypher,
                    id=entity_id,
                    rels=[r.upper() for r in rel_types],
                )
            else:
                cypher = f"""
                MATCH p = (a {{id: $id}})-[*1..{hops}]-(b)
                RETURN [n IN nodes(p) | n.id] AS nodes,
                       [r IN relationships(p) | type(r)] AS rels
                LIMIT 40
                """
                result = session.run(cypher, id=entity_id)
            paths: list[dict] = []
            for rec in result:
                nodes = list(rec["nodes"] or [])
                rels = list(rec["rels"] or [])
                paths.append(
                    {
                        "nodes": nodes,
                        "rels": rels,
                        "rationale": f"neo4j path from {entity_id}",
                        "source": "neo4j",
                    }
                )
            return paths
    except Exception:
        return None
    finally:
        driver.close()


def lookup_entity_impl(name_or_id: str) -> dict | None:
    hit = _lookup_neo4j(name_or_id)
    if hit is not None:
        return hit
    seed = _lookup_seed(name_or_id)
    if seed is None:
        return None
    seed = dict(seed)
    seed["source"] = "seed_jsonl"
    return seed


def traverse_relations_impl(
    entity_id: str,
    rel_types: list[str] | None = None,
    hops: int = 2,
) -> list[dict]:
    neo = _traverse_neo4j(entity_id, rel_types=rel_types, hops=hops)
    if neo is not None:
        return neo
    return _traverse_seed(entity_id, rel_types=rel_types, hops=hops)


@tool
def lookup_entity(name_or_id: str) -> dict | None:
    """Look up a knowledge-graph entity by id or name (Neo4j, else seed JSONL)."""
    return lookup_entity_impl(name_or_id)


@tool
def traverse_relations(
    entity_id: str,
    rel_types: list[str] | None = None,
    hops: int = 2,
) -> list[dict]:
    """Traverse graph relations from entity_id up to `hops` (default 2).

    Optional rel_types filter e.g. ["SUPERSEDES","APPLIES_TO","GOVERNS","REQUIRES","LOCATED_AT"].
    """
    return traverse_relations_impl(entity_id, rel_types=rel_types, hops=hops)


def extract_entity_candidates(query: str, chunks: list[dict] | None = None) -> list[str]:
    """Heuristic entity ids from query text + chunk metadata.entities."""
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(val: str) -> None:
        v = (val or "").strip()
        if not v or v in seen:
            return
        seen.add(v)
        candidates.append(v)

    # Known ids appearing in query
    entities, _ = _load_seed_graph()
    q = query or ""
    q_upper = q.upper()
    for eid in entities:
        if eid.upper() in q_upper or eid.replace("-", " ").upper() in q_upper:
            _add(eid)

    # PN-#### / SOP- / STD- / POL- / RB- patterns
    for m in re.findall(
        r"\b(?:PN|SOP|STD|POL|RB|KB|WI|DES|FW|BOM)-[A-Za-z0-9-]+\b",
        q,
        flags=re.I,
    ):
        _add(m.upper() if m.upper().startswith("PN-") else m)

    for ch in chunks or []:
        meta = ch.get("metadata") or {}
        ents = meta.get("entities") or []
        if isinstance(ents, str):
            try:
                ents = json.loads(ents)
            except json.JSONDecodeError:
                ents = [e.strip() for e in ents.split(",") if e.strip()]
        for e in ents:
            _add(str(e))
        doc_id = ch.get("doc_id") or meta.get("doc_id")
        if doc_id:
            _add(str(doc_id))
    return candidates


__all__ = [
    "extract_entity_candidates",
    "lookup_entity",
    "lookup_entity_impl",
    "traverse_relations",
    "traverse_relations_impl",
]
