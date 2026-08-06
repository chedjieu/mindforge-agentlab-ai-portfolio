"""LangGraph master supervisor for HEDIP."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from app.agents import (
    firewall_node,
    hitl_node,
    intent_router,
    master_supervisor,
    publish_node,
    shared_judge,
)
from app.domains import DOMAIN_RUNNERS
from app.state import Domain, HedipState


def _after_firewall(state: HedipState) -> Literal["intent_router", "publish"]:
    return "publish" if state.get("blocked") else "intent_router"


def _from_supervisor(state: HedipState):
    nxt = state.get("next") or "END"
    if nxt == "END":
        return END
    return nxt


def make_initial_state(
    *,
    thread_id: str,
    query: str,
    domain: Domain | None = None,
    case_id: str = "",
    user_id: str = "demo-user",
    role: str = "payer_reviewer",
) -> HedipState:
    return {
        "thread_id": thread_id,
        "user_id": user_id,
        "role": role,
        "domain": domain,
        "query": query,
        "case_id": case_id,
        "abac": {"role": role},
        "sensitivity": "normal",
        "intent": {},
        "case_payload": {},
        "domain_result": {},
        "evidence": [],
        "graph_paths": [],
        "draft": "",
        "recommendation": {},
        "citations": [],
        "judges": {},
        "compliance": {},
        "safety_score": None,
        "needs_hitl": False,
        "approval": "pending",
        "published": False,
        "final_response": "",
        "step_log": [],
        "blocked": False,
        "block_reason": "",
        "next": "intent_router",
    }


def build_graph(checkpointer: Any = None):
    g = StateGraph(HedipState)
    g.add_node("firewall", firewall_node)
    g.add_node("intent_router", intent_router)
    g.add_node("supervisor", master_supervisor)
    for name, fn in DOMAIN_RUNNERS.items():
        g.add_node(name, fn)
    g.add_node("shared_judge", shared_judge)
    g.add_node("hitl", hitl_node)
    g.add_node("publish", publish_node)

    g.add_edge(START, "firewall")
    g.add_conditional_edges("firewall", _after_firewall, ["intent_router", "publish"])
    g.add_edge("intent_router", "supervisor")
    targets = list(DOMAIN_RUNNERS.keys()) + ["shared_judge", "hitl", "publish", "intent_router", END]
    g.add_conditional_edges("supervisor", _from_supervisor, targets)
    for name in DOMAIN_RUNNERS:
        g.add_edge(name, "supervisor")
    g.add_edge("shared_judge", "supervisor")
    g.add_edge("hitl", "supervisor")
    g.add_edge("publish", END)
    return g.compile(checkpointer=checkpointer)


def build_graph_with_backends(checkpointer: Any = None):
    if checkpointer is None:
        import os

        mode = os.getenv("HEDIP_MEMORY", "memory").strip().lower()
        dsn = os.getenv("POSTGRES_DSN", "").strip()
        if mode == "postgres" and dsn:
            try:
                from langgraph.checkpoint.postgres import PostgresSaver

                checkpointer = PostgresSaver.from_conn_string(dsn)
            except Exception:
                checkpointer = None
        if checkpointer is None:
            from langgraph.checkpoint.memory import MemorySaver

            checkpointer = MemorySaver()
    return build_graph(checkpointer=checkpointer)


if __name__ == "__main__":
    import uuid

    from langgraph.types import Command

    graph = build_graph_with_backends()
    tid = str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    state = make_initial_state(
        thread_id=tid,
        domain="prior_auth",
        case_id="PA-MRI-001",
        query="Review prior authorization for lumbar MRI",
    )
    print("HEDIP smoke (prior_auth)...")
    for upd in graph.stream(state, config, stream_mode="updates"):
        print(" ", next(iter(upd.keys())))
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        print("HITL auto-approve")
        graph.invoke(Command(resume={"action": "approve"}), config)
        snap = graph.get_state(config)
    v = snap.values
    print("published:", v.get("published"), "decision:", (v.get("recommendation") or {}).get("decision"))
