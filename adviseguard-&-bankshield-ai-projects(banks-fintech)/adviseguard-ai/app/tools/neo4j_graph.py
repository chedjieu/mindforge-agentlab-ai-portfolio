"""Neo4j GraphRAG tools with JSON-seed in-memory fallback."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
KG_DIR = ROOT / "data" / "kg"
MAX_TOOL_CALLS = 6


@lru_cache(maxsize=1)
def _load_seed_graph() -> dict[str, Any]:
    nodes: list[dict] = []
    edges: list[dict] = []
    for path in sorted(KG_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        nodes.extend(data.get("nodes") or [])
        edges.extend(data.get("edges") or [])
    return {"nodes": {n["id"]: n for n in nodes if "id" in n}, "edges": edges}


def _neo4j_available() -> bool:
    try:
        from neo4j import GraphDatabase

        uri = os.getenv("ADVISEGUARD_NEO4J_URI", "bolt://localhost:7688")
        user = os.getenv("ADVISEGUARD_NEO4J_USER", "neo4j")
        password = os.getenv("ADVISEGUARD_NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        return True
    except Exception:
        return False


def load_kg_seeds_to_neo4j() -> int:
    if not _neo4j_available():
        return 0
    from neo4j import GraphDatabase

    uri = os.getenv("ADVISEGUARD_NEO4J_URI", "bolt://localhost:7688")
    user = os.getenv("ADVISEGUARD_NEO4J_USER", "neo4j")
    password = os.getenv("ADVISEGUARD_NEO4J_PASSWORD", "password")
    graph = _load_seed_graph()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    count = 0
    with driver.session() as session:
        for node in graph["nodes"].values():
            label = node.get("label", "Entity")
            props = {k: v for k, v in node.items() if k != "label"}
            session.run(
                f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                id=node["id"],
                props=props,
            )
        for edge in graph["edges"]:
            rel = edge.get("type", "RELATED_TO")
            session.run(
                f"MATCH (a {{id: $src}}), (b {{id: $dst}}) MERGE (a)-[r:{rel}]->(b)",
                src=edge["source"],
                dst=edge["target"],
            )
            count += 1
    driver.close()
    return count


def find_paths(start_id: str, *, max_hops: int = 3) -> list[dict[str, Any]]:
    if not start_id:
        return []
    if _neo4j_available():
        return _neo4j_paths(start_id, max_hops=max_hops)
    return _memory_paths(start_id, max_hops=max_hops)


def _neo4j_paths(start_id: str, *, max_hops: int) -> list[dict[str, Any]]:
    from neo4j import GraphDatabase

    uri = os.getenv("ADVISEGUARD_NEO4J_URI", "bolt://localhost:7688")
    user = os.getenv("ADVISEGUARD_NEO4J_USER", "neo4j")
    password = os.getenv("ADVISEGUARD_NEO4J_PASSWORD", "password")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    paths: list[dict[str, Any]] = []
    cypher = f"""
    MATCH p = (a {{id: $sid}})-[*1..{max_hops}]-(b)
    WHERE a <> b
    RETURN [n IN nodes(p) | n.id] AS node_ids,
           [r IN relationships(p) | type(r)] AS rels,
           length(p) AS hops
    LIMIT 10
    """
    with driver.session() as session:
        for rec in session.run(cypher, sid=start_id):
            paths.append(
                {
                    "nodes": list(rec["node_ids"]),
                    "relationships": list(rec["rels"]),
                    "hops": int(rec["hops"]),
                    "explanation": "Neo4j multi-hop path",
                }
            )
    driver.close()
    return paths


def _memory_paths(start_id: str, *, max_hops: int) -> list[dict[str, Any]]:
    graph = _load_seed_graph()
    nodes = graph["nodes"]
    edges = graph["edges"]
    adj: dict[str, list[tuple[str, str]]] = {}
    for e in edges:
        adj.setdefault(e["source"], []).append((e["target"], e.get("type", "RELATED_TO")))
        adj.setdefault(e["target"], []).append((e["source"], e.get("type", "RELATED_TO")))
    if start_id not in adj and start_id not in nodes:
        return []
    paths: list[dict[str, Any]] = []
    stack: list[tuple[str, list[str], list[str]]] = [(start_id, [start_id], [])]
    while stack and len(paths) < 10:
        cur, npath, rpath = stack.pop()
        if len(npath) - 1 >= max_hops:
            continue
        for nxt, rel in adj.get(cur, []):
            if nxt in npath:
                continue
            nn, rr = npath + [nxt], rpath + [rel]
            interesting = any(
                r in ("SUITABLE_FOR", "SHARES_DEVICE", "MATCHES_PATTERN", "TRANSFERRED_TO", "OWNS")
                for r in rr
            )
            if interesting and len(nn) >= 2:
                labels = [str(nodes.get(x, {}).get("label", x)) for x in nn]
                expl = "; ".join(f"{labels[i]} -[{rr[i]}]-> {labels[i+1]}" for i in range(len(rr)))
                paths.append(
                    {"nodes": nn, "relationships": rr, "hops": len(rr), "explanation": expl}
                )
            stack.append((nxt, nn, rr))
    return paths[:10]
