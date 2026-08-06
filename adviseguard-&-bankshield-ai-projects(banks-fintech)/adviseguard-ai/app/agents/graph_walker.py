"""Graph walker for product fit and fraud relationship hops."""

from __future__ import annotations

from app.state import SessionState
from app.tools.neo4j_graph import MAX_TOOL_CALLS, find_paths


def graph_walker_node(state: SessionState) -> dict:
    customer_id = state.get("customer_id") or "CUST-1001"
    alert = state.get("txn_alert") or {}
    calls = 0
    paths = find_paths(str(customer_id), max_hops=3)
    calls += 1
    device = alert.get("device_id")
    if device and calls < MAX_TOOL_CALLS:
        more = find_paths(str(device), max_hops=2)
        calls += 1
        for p in more:
            if p not in paths:
                paths.append(p)
    if not paths:
        paths = [
            {
                "nodes": [customer_id],
                "relationships": [],
                "hops": 0,
                "explanation": "No multi-hop paths found",
            }
        ]
    return {
        "graph_paths": paths[:10],
        "step_log": state["step_log"]
        + [f"GraphWalker: paths={len(paths)} calls={calls}/{MAX_TOOL_CALLS}"],
    }
