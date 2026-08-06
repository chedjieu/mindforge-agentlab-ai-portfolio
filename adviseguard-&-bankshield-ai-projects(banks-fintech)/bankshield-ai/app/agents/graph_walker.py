"""Knowledge-graph walker — mule / shared-entity discovery (budget ≤6)."""

from __future__ import annotations

from app.state import InvestigationState
from app.tools.neo4j_graph import MAX_TOOL_CALLS, detect_mule_ring, find_shared_entity_paths


def graph_walker_node(state: InvestigationState) -> dict:
    entities = state.get("entities") or {}
    alert = state.get("alert") or {}
    customer_id = entities.get("customer_id") or alert.get("customer_id")
    calls = 0
    paths: list[dict] = []
    mule: dict = {}

    if customer_id and calls < MAX_TOOL_CALLS:
        mule = detect_mule_ring(str(customer_id))
        calls += 1
        paths.extend(mule.get("paths") or [])

    if calls < MAX_TOOL_CALLS:
        more = find_shared_entity_paths(
            customer_id=str(customer_id) if customer_id else None,
            device_id=entities.get("device_id") or alert.get("device_id"),
            ip=entities.get("ip") or alert.get("ip"),
            phone=entities.get("phone") or alert.get("phone"),
            beneficiary=entities.get("beneficiary") or alert.get("beneficiary"),
            max_hops=3,
        )
        calls += 1
        for p in more:
            if p not in paths:
                paths.append(p)

    # Sentinel so supervisor does not loop forever
    if not paths:
        paths = [
            {
                "nodes": [str(customer_id or "unknown")],
                "relationships": [],
                "hops": 0,
                "explanation": "No multi-hop shared-entity paths found",
            }
        ]

    evidence = list(state.get("evidence") or [])
    evidence.append(
        {
            "id": f"graph-{customer_id or 'na'}",
            "source": "graph_walker",
            "summary": (
                f"paths={len(paths)} mule_suspect={mule.get('is_mule_suspect')} "
                f"mule_score={mule.get('mule_score')} tool_calls={calls}"
            ),
            "mule": {k: v for k, v in mule.items() if k != "paths"} if mule else {},
        }
    )
    fraud_types = list(state.get("fraud_types") or [])
    if mule.get("is_mule_suspect") and "mule" not in fraud_types:
        fraud_types.append("mule")

    return {
        "graph_paths": paths[:10],
        "evidence": evidence,
        "fraud_types": fraud_types,
        "step_log": state["step_log"]
        + [
            f"GraphWalker: paths={len(paths)} mule={mule.get('is_mule_suspect')} "
            f"calls={calls}/{MAX_TOOL_CALLS}"
        ],
    }
