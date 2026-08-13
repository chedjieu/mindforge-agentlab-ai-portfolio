"""LangGraph supervisor loop for RAIP authoring."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    claim_verification_node,
    drafting_node,
    editorial_node,
    evidence_retrieval_node,
    evidence_synthesis_node,
    firewall_node,
    hitl_node,
    persist_node,
    publication_gate_node,
    quality_gates_node,
    supervisor_node,
)
from app.orchestration.state import AuthoringState, make_initial_state

WORKER_NODES = (
    "evidence_retrieval",
    "evidence_synthesis",
    "drafting",
    "claim_verification",
    "quality_gates",
    "editorial",
    "publication_gate",
    "hitl",
    "persist",
)


def _route_from_supervisor(state: AuthoringState) -> Any:
    nxt = state.get("next") or "END"
    if nxt == "END":
        return END
    if nxt in WORKER_NODES:
        return nxt
    return END


def _route_after_firewall(state: AuthoringState) -> Literal["supervisor", "publication_gate"]:
    if state.get("blocked"):
        return "publication_gate"
    return "supervisor"


def build_graph(checkpointer: Any = None):
    g = StateGraph(AuthoringState)
    g.add_node("firewall", firewall_node)
    g.add_node("supervisor", supervisor_node)
    g.add_node("evidence_retrieval", evidence_retrieval_node)
    g.add_node("evidence_synthesis", evidence_synthesis_node)
    g.add_node("drafting", drafting_node)
    g.add_node("claim_verification", claim_verification_node)
    g.add_node("quality_gates", quality_gates_node)
    g.add_node("editorial", editorial_node)
    g.add_node("publication_gate", publication_gate_node)
    g.add_node("hitl", hitl_node)
    g.add_node("persist", persist_node)
    g.add_edge(START, "firewall")
    g.add_conditional_edges("firewall", _route_after_firewall, ["supervisor", "publication_gate"])
    g.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {name: name for name in WORKER_NODES} | {END: END},  # type: ignore[arg-type]
    )
    for name in WORKER_NODES:
        g.add_edge(name, "supervisor")
    return g.compile(checkpointer=checkpointer)


def build_graph_with_backends(checkpointer: Any = None):
    if checkpointer is None:
        import os

        memory_mode = os.getenv("RAIP_MEMORY", "memory").strip().lower()
        dsn = os.getenv("POSTGRES_DSN", "").strip()
        if memory_mode == "postgres" and dsn:
            try:
                from langgraph.checkpoint.postgres import PostgresSaver

                checkpointer = PostgresSaver.from_conn_string(dsn)
            except Exception:
                checkpointer = None
        if checkpointer is None:
            from langgraph.checkpoint.memory import MemorySaver

            checkpointer = MemorySaver()
    return build_graph(checkpointer=checkpointer)


SAMPLE_QUERY = (
    "Draft the Clinical Management Recommendations section for adult type 2 diabetes "
    "pharmacologic therapy using only approved sources."
)

UNSUPPORTED_QUERY = (
    "Recommend CRISPR gene editing as first-line therapy for type 2 diabetes mellitus."
)

if __name__ == "__main__":
    import os
    import uuid

    os.environ.setdefault("RAIP_MODEL", "fake")
    os.environ.setdefault("RAIP_HITL", "evaluate")
    from app.storage.db import init_db
    from scripts.seed_demo import seed

    init_db()
    tenant, project = seed()
    graph = build_graph_with_backends()
    tid = str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    state = make_initial_state(
        request_id=tid,
        thread_id=tid,
        tenant_id=tenant,
        user_id="author-01",
        project_id=project,
        query=SAMPLE_QUERY,
    )
    print("Running RAIP fake smoke...")
    for update in graph.stream(state, config, stream_mode="updates"):
        node = next(iter(update.keys()), "?")
        print(f"  update: {node}")
    snap = graph.get_state(config)
    values = snap.values
    print("status:", values.get("workflow_status"))
    print("grounding:", values.get("grounding_score"))
    print("blocked_pub:", (values.get("scores") or {}).get("publication_blocked"))
    print((values.get("draft") or "")[:400])
