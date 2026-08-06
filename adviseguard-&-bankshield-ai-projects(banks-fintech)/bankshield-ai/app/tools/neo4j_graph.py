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
    by_id = {n["id"]: n for n in nodes if "id" in n}
    return {"nodes": by_id, "edges": edges}


def _neo4j_available() -> bool:
    uri = os.getenv("BANKSHIELD_NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("BANKSHIELD_NEO4J_USER", "neo4j")
    password = os.getenv("BANKSHIELD_NEO4J_PASSWORD", "password")
    try:
        from neo4j import GraphDatabase

        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        return True
    except Exception:
        return False


def load_kg_seeds_to_neo4j() -> int:
    """Idempotent MERGE of seed nodes/edges into Neo4j. Returns edge count."""
    if not _neo4j_available():
        return 0
    from neo4j import GraphDatabase

    uri = os.getenv("BANKSHIELD_NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("BANKSHIELD_NEO4J_USER", "neo4j")
    password = os.getenv("BANKSHIELD_NEO4J_PASSWORD", "password")
    graph = _load_seed_graph()
    driver = GraphDatabase.driver(uri, auth=(user, password))
    count = 0
    with driver.session() as session:
        for node in graph["nodes"].values():
            label = node.get("label", "Entity")
            props = {k: v for k, v in node.items() if k not in ("label",)}
            session.run(
                f"MERGE (n:{label} {{id: $id}}) SET n += $props",
                id=node["id"],
                props=props,
            )
        for edge in graph["edges"]:
            rel = edge.get("type", "RELATED_TO")
            session.run(
                f"""
                MATCH (a {{id: $src}}), (b {{id: $dst}})
                MERGE (a)-[r:{rel}]->(b)
                SET r += $props
                """,
                src=edge["source"],
                dst=edge["target"],
                props={k: v for k, v in edge.items() if k not in ("source", "target", "type")},
            )
            count += 1
    driver.close()
    return count


def find_shared_entity_paths(
    *,
    customer_id: str | None = None,
    device_id: str | None = None,
    ip: str | None = None,
    phone: str | None = None,
    beneficiary: str | None = None,
    max_hops: int = 3,
) -> list[dict[str, Any]]:
    """Discover mule-like shared-entity paths (Neo4j or seed fallback)."""
    seeds = [x for x in (customer_id, device_id, ip, phone, beneficiary) if x]
    if not seeds:
        return []

    if _neo4j_available():
        return _neo4j_paths(seeds[0], max_hops=max_hops)
    return _memory_paths(seeds, max_hops=max_hops)


def _neo4j_paths(start_id: str, *, max_hops: int) -> list[dict[str, Any]]:
    from neo4j import GraphDatabase

    uri = os.getenv("BANKSHIELD_NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("BANKSHIELD_NEO4J_USER", "neo4j")
    password = os.getenv("BANKSHIELD_NEO4J_PASSWORD", "password")
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
                    "explanation": "Neo4j multi-hop shared-entity path",
                }
            )
    driver.close()
    return paths


def _memory_paths(seeds: list[str], *, max_hops: int) -> list[dict[str, Any]]:
    graph = _load_seed_graph()
    nodes = graph["nodes"]
    edges = graph["edges"]
    adj: dict[str, list[tuple[str, str]]] = {}
    for e in edges:
        adj.setdefault(e["source"], []).append((e["target"], e.get("type", "RELATED_TO")))
        adj.setdefault(e["target"], []).append((e["source"], e.get("type", "RELATED_TO")))

    paths: list[dict[str, Any]] = []
    for start in seeds:
        if start not in nodes and start not in adj:
            continue
        stack: list[tuple[str, list[str], list[str]]] = [(start, [start], [])]
        seen_paths: set[tuple[str, ...]] = set()
        while stack and len(paths) < 10:
            cur, node_path, rel_path = stack.pop()
            if len(node_path) - 1 >= max_hops:
                continue
            for nxt, rel in adj.get(cur, []):
                if nxt in node_path:
                    continue
                npath = node_path + [nxt]
                rpath = rel_path + [rel]
                key = tuple(npath)
                if key in seen_paths:
                    continue
                seen_paths.add(key)
                # Prefer interesting mule signals
                interesting = any(
                    r in ("SHARES_DEVICE", "SHARES_IP", "SHARES_PHONE", "SHARES_BENEFICIARY", "TRANSFERRED_TO")
                    for r in rpath
                )
                if interesting and len(npath) >= 2:
                    paths.append(
                        {
                            "nodes": npath,
                            "relationships": rpath,
                            "hops": len(rpath),
                            "explanation": _explain_path(npath, rpath, nodes),
                        }
                    )
                stack.append((nxt, npath, rpath))
    return paths[:10]


def _explain_path(node_ids: list[str], rels: list[str], nodes: dict[str, Any]) -> str:
    labels = [str(nodes.get(n, {}).get("label", n)) for n in node_ids]
    parts = []
    for i, rel in enumerate(rels):
        parts.append(f"{labels[i]} -[{rel}]-> {labels[i + 1]}")
    return "; ".join(parts) if parts else "shared entity link"


def detect_mule_ring(customer_id: str) -> dict[str, Any]:
    """Heuristic mule-ring score from shared devices/IPs/phones/beneficiaries."""
    paths = find_shared_entity_paths(customer_id=customer_id, max_hops=3)
    shared_rels = 0
    for p in paths:
        shared_rels += sum(
            1
            for r in p.get("relationships", [])
            if r.startswith("SHARES_") or r == "TRANSFERRED_TO"
        )
    score = min(1.0, 0.2 + 0.15 * shared_rels + 0.1 * len(paths))
    return {
        "customer_id": customer_id,
        "path_count": len(paths),
        "shared_signal_count": shared_rels,
        "mule_score": round(score, 3),
        "paths": paths[:5],
        "is_mule_suspect": score >= 0.55 or len(paths) >= 2,
    }
