"""Retrieval worker — tenant-scoped hybrid RAG + Neo4j (≤ 8 tools)."""

from __future__ import annotations

from app.tools.integrations import fhir_stub_read, salesforce_stub_read, sis_stub_read
from app.tools.kg import lookup_entity, traverse_relations
from app.tools.retrieval import get_engagement_history, hybrid_search
from app.state import EngagementState

MAX_TOOLS = 8


def _allowed(name: str, allowlist: list[str]) -> bool:
    return name in allowlist


def retrieval_node(state: EngagementState) -> dict:
    cfg = state.get("guardrail_config") or {}
    allowlist = list(cfg.get("tool_allowlist") or [])
    tenant_id = state["tenant_id"]
    vertical = state["vertical"] or "edtech"
    brief = state["raw_brief"]
    query = " ".join(
        str(brief.get(k) or "")
        for k in ("title", "subject", "body", "description", "constraints")
    ).strip()

    evidence: list[dict] = []
    calls = 0
    log: list[str] = []

    def _run(name: str, fn, *args, **kwargs):
        nonlocal calls
        if calls >= MAX_TOOLS:
            return None
        if not _allowed(name, allowlist):
            log.append(f"retrieval: skipped {name} (not on allowlist)")
            return None
        calls += 1
        result = fn(*args, **kwargs)
        log.append(f"retrieval: {name} ok")
        return result

    chunks = _run(
        "hybrid_search",
        hybrid_search,
        query=query,
        tenant_id=tenant_id,
        vertical=vertical,
        reusable_ids=[d.get("component_id") for d in state.get("reuse_decisions") or []],
    )
    if chunks:
        for i, ch in enumerate(chunks[:5]):
            evidence.append({"id": f"ev-{i+1}", "type": "chunk", **ch})

    entity = _run(
        "lookup_entity",
        lookup_entity,
        query=query,
        tenant_id=tenant_id,
        vertical=vertical,
    )
    if entity:
        evidence.append({"id": "ev-ent", "type": "entity", **entity})

    paths = _run(
        "traverse_relations",
        traverse_relations,
        entity_id=(entity or {}).get("id"),
        tenant_id=tenant_id,
        hops=2,
    )
    if paths:
        evidence.append({"id": "ev-graph", "type": "graph_paths", "paths": paths})

    hist = _run(
        "get_engagement_history",
        get_engagement_history,
        tenant_id=tenant_id,
        vertical=vertical,
        query=query,
    )
    if hist:
        evidence.append({"id": "ev-hist", "type": "history", "items": hist})

    if vertical == "edtech":
        sis = _run("sis_stub_read", sis_stub_read, tenant_id=tenant_id)
        if sis:
            evidence.append({"id": "ev-sis", "type": "sis", **sis})
    elif vertical == "healthcare":
        fhir = _run("fhir_stub_read", fhir_stub_read, tenant_id=tenant_id)
        if fhir:
            evidence.append({"id": "ev-fhir", "type": "fhir", **fhir})
    elif vertical in ("finserv", "retail"):
        sf = _run("salesforce_stub_read", salesforce_stub_read, tenant_id=tenant_id)
        if sf:
            evidence.append({"id": "ev-sf", "type": "salesforce", **sf})

    if not evidence:
        evidence.append(
            {
                "id": "ev-fallback",
                "type": "chunk",
                "text": f"Baseline {vertical} playbook for tenant {tenant_id}.",
                "tenant_id": tenant_id,
                "score": 0.5,
            }
        )

    return {
        "evidence": evidence,
        "step_log": state["step_log"]
        + log
        + [f"retrieval: {len(evidence)} evidence items ({calls} tool calls)"],
    }
