"""Knowledge graph tools — Neo4j if available, else JSONL seeds."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

KG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "kg"


@lru_cache(maxsize=1)
def _load_entities() -> list[dict]:
    path = KG_DIR / "seed_entities.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


@lru_cache(maxsize=1)
def _load_relations() -> list[dict]:
    path = KG_DIR / "seed_relations.jsonl"
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _neo4j_driver():
    uri = os.getenv("NEO4J_URI", "").strip()
    if not uri:
        return None
    try:
        from neo4j import GraphDatabase

        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        return GraphDatabase.driver(uri, auth=(user, password))
    except Exception:
        return None


def list_reusable_components(vertical: str, exclude_tenant: str) -> list[dict]:
    comps = []
    for e in _load_entities():
        if e.get("label") != "AgentComponent":
            continue
        if e.get("vertical") and e.get("vertical") != vertical and e.get("vertical") != "shared":
            continue
        if e.get("tenant_id") == exclude_tenant and not e.get("reusable_ip"):
            continue
        # Prefer components marked reusable or from other tenants that are productized
        if e.get("reusable_ip") or e.get("productized"):
            comps.append(dict(e))
    if not comps:
        # Seed fallback synthetic IP
        comps = [
            {
                "id": f"comp-{vertical}-onboarding",
                "component_id": f"comp-{vertical}-onboarding",
                "label": "AgentComponent",
                "name": f"{vertical} onboarding pattern",
                "vertical": vertical,
                "reusable_ip": True,
                "productized": True,
                "tenant_id": "ip-library",
                "embeddings_tenant": "prior-tenant-x",
            }
        ]
    return comps


def sanitize_component(comp: dict, for_tenant: str) -> dict:
    """Strip prior tenant embeddings and mark sanitized for the requesting tenant."""
    out = dict(comp)
    out["component_id"] = out.get("component_id") or out.get("id")
    out["prior_embeddings_tenant"] = out.pop("embeddings_tenant", None)
    out["embeddings_tenant"] = None
    out["sanitized"] = True
    out["reusable_ip"] = True
    out["sanitized_for_tenant"] = for_tenant
    out["prior_tenant_id"] = out.get("tenant_id") if out.get("tenant_id") != for_tenant else None
    # Component becomes available as reusable IP without carrying prior tenant data
    out["tenant_id"] = "ip-library"
    return out


def lookup_entity(query: str, tenant_id: str, vertical: str) -> dict | None:
    driver = _neo4j_driver()
    qlow = (query or "").lower()
    if driver:
        try:
            with driver.session() as session:
                rec = session.run(
                    """
                    MATCH (n)
                    WHERE (n.tenant_id = $tenant_id OR n.reusable_ip = true)
                      AND (toLower(n.name) CONTAINS $q OR toLower(coalesce(n.id,'')) CONTAINS $q)
                    RETURN n LIMIT 1
                    """,
                    tenant_id=tenant_id,
                    q=qlow[:40],
                ).single()
                if rec:
                    node = dict(rec["n"])
                    return {"id": node.get("id") or node.get("name"), **node}
        except Exception:
            pass

    for e in _load_entities():
        et = e.get("tenant_id")
        if et not in (tenant_id, "ip-library", None) and not e.get("reusable_ip"):
            continue
        if e.get("vertical") and e.get("vertical") not in (vertical, "shared"):
            name = (e.get("name") or "").lower()
            eid = (e.get("id") or "").lower()
            if any(tok in name or tok in eid for tok in qlow.split()[:5] if len(tok) > 3):
                return dict(e)
            continue
        name = (e.get("name") or "").lower()
        eid = (e.get("id") or "").lower()
        blob = f"{name} {eid} {e.get('label', '')}".lower()
        if vertical in blob or any(tok in blob for tok in qlow.split()[:4] if len(tok) > 3):
            if et in (tenant_id, "ip-library", None) or e.get("reusable_ip"):
                return dict(e)

    # Fallback entity for vertical
    for e in _load_entities():
        if e.get("vertical") == vertical and (
            e.get("tenant_id") in (tenant_id, "ip-library") or e.get("reusable_ip")
        ):
            return dict(e)
    return {
        "id": f"eng-{vertical}",
        "name": f"{vertical} engagement pattern",
        "tenant_id": tenant_id,
        "label": "Engagement",
        "vertical": vertical,
    }


def traverse_relations(entity_id: str | None, tenant_id: str, hops: int = 2) -> list[dict]:
    if not entity_id:
        return []
    driver = _neo4j_driver()
    if driver:
        try:
            with driver.session() as session:
                result = session.run(
                    """
                    MATCH (n {id: $eid})-[r*1..2]-(m)
                    WHERE m.tenant_id = $tenant_id OR m.reusable_ip = true OR m.tenant_id IS NULL
                    RETURN n.id AS src, type(r[0]) AS rel, m.id AS dst, labels(m) AS labels
                    LIMIT 20
                    """,
                    eid=entity_id,
                    tenant_id=tenant_id,
                )
                return [dict(rec) for rec in result]
        except Exception:
            pass

    paths = []
    for rel in _load_relations():
        if rel.get("source") == entity_id or rel.get("target") == entity_id:
            # Enforce tenant on related nodes when present
            tgt = next((e for e in _load_entities() if e.get("id") == rel.get("target")), None)
            src = next((e for e in _load_entities() if e.get("id") == rel.get("source")), None)
            for node in (tgt, src):
                if not node:
                    continue
                if node.get("tenant_id") not in (tenant_id, "ip-library", None) and not node.get(
                    "reusable_ip"
                ):
                    continue
            paths.append(
                {
                    "source": rel.get("source"),
                    "rel": rel.get("type"),
                    "target": rel.get("target"),
                }
            )
            if len(paths) >= 10:
                break
    return paths
