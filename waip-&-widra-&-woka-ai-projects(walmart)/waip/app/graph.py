"""LangGraph master + parallel worker fan-out."""

from __future__ import annotations

from typing import Any, Literal

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from app.agents import (
    WORKER_MAP,
    action_executor,
    aggregator,
    compliance_agent,
    firewall_node,
    hitl_node,
    master_planner,
    publish_node,
    response_validator,
)
from app.state import AssociateState


def _route_after_firewall(state: AssociateState) -> Literal["master_planner", "publish"]:
    if state.get("blocked"):
        return "publish"
    return "master_planner"


def _fanout(state: AssociateState) -> list[Send]:
    workers = state.get("workers") or ["hr", "search"]
    sends: list[Send] = []
    for w in workers:
        if w in WORKER_MAP:
            sends.append(Send(w, state))
    if not sends:
        sends.append(Send("hr", state))
    return sends


def _route_after_compliance(state: AssociateState) -> Literal["hitl", "publish"]:
    return "hitl" if state.get("next") == "hitl" else "publish"


def _route_after_hitl(state: AssociateState) -> Literal["action_executor", "publish"]:
    return "action_executor" if state.get("next") == "action_executor" else "publish"


def build_graph(checkpointer: Any = None):
    g = StateGraph(AssociateState)

    g.add_node("firewall", firewall_node)
    g.add_node("master_planner", master_planner)
    for name, fn in WORKER_MAP.items():
        g.add_node(name, fn)
    g.add_node("aggregator", aggregator)
    g.add_node("response_validator", response_validator)
    g.add_node("compliance_agent", compliance_agent)
    g.add_node("hitl", hitl_node)
    g.add_node("action_executor", action_executor)
    g.add_node("publish", publish_node)

    g.add_edge(START, "firewall")
    g.add_conditional_edges("firewall", _route_after_firewall, ["master_planner", "publish"])
    g.add_conditional_edges("master_planner", _fanout, list(WORKER_MAP.keys()))
    for name in WORKER_MAP:
        g.add_edge(name, "aggregator")
    g.add_edge("aggregator", "response_validator")
    g.add_edge("response_validator", "compliance_agent")
    g.add_conditional_edges("compliance_agent", _route_after_compliance, ["hitl", "publish"])
    g.add_conditional_edges("hitl", _route_after_hitl, ["action_executor", "publish"])
    g.add_edge("action_executor", "publish")
    g.add_edge("publish", END)

    return g.compile(checkpointer=checkpointer)


def build_graph_with_backends(checkpointer: Any = None):
    if checkpointer is None:
        import os

        memory_mode = os.getenv("WAIP_MEMORY", "memory").strip().lower()
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


if __name__ == "__main__":
    import uuid
    from langgraph.types import Command

    graph = build_graph_with_backends()
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    init = {
        "associate_id": "A1001",
        "abac": {
            "country": "US",
            "state": "AR",
            "department": "Pharmacy",
            "role": "Pharmacy Tech",
            "bu": "US Stores",
            "store": "1001",
        },
        "query": (
            "My paycheck is short because I took medical leave last week. "
            "Can you explain why and open a payroll ticket if necessary?"
        ),
        "step_log": [],
        "evidence": [],
        "worker_results": {},
    }
    result = graph.invoke(init, config=thread)
    # If interrupted for HITL, auto-approve in CLI demo
    if graph.get_state(thread).tasks:
        result = graph.invoke(Command(resume={"approved": True, "note": "cli-auto"}), config=thread)
    print(result.get("final_response"))
    print("tickets:", result.get("ticket_ids"))
    print("steps:", result.get("step_log"))
