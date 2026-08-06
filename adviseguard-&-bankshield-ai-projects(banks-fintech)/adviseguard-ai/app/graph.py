"""AdviseGuard LangGraph — supervisor routes workers in a loop."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore

from app.agents.compliance_judge import compliance_judge_node
from app.agents.customer_support import customer_support_node
from app.agents.financial_advisor import financial_advisor_node
from app.agents.fraud_detector import fraud_detector_node
from app.agents.graph_walker import graph_walker_node
from app.agents.hitl import hitl_node
from app.agents.hybrid_retriever import hybrid_retriever_node
from app.agents.intent_router import intent_router_node
from app.agents.response_publish import response_publish_node
from app.agents.risk_judge import risk_judge_node
from app.agents.supervisor import supervisor_node
from app.agents.synthesizer import synthesizer_node
from app.state import SessionState

CHECKPOINT_PATH = Path(__file__).resolve().parent.parent / "checkpoints.sqlite"
CUSTOMERS_PATH = Path(__file__).resolve().parent.parent / "data" / "customers" / "customers.json"
ALERTS_PATH = Path(__file__).resolve().parent.parent / "data" / "alerts" / "alerts.json"

WORKERS = (
    "intent_router",
    "hybrid_retriever",
    "graph_walker",
    "financial_advisor",
    "fraud_detector",
    "customer_support",
    "compliance_judge",
    "risk_judge",
    "synthesizer",
    "hitl",
    "response_publish",
)


def build_graph_with_backends(saver: Any, store: BaseStore | None = None):
    builder = StateGraph(SessionState)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("intent_router", intent_router_node)
    builder.add_node("hybrid_retriever", hybrid_retriever_node)
    builder.add_node("graph_walker", graph_walker_node)
    builder.add_node("financial_advisor", financial_advisor_node)
    builder.add_node("fraud_detector", fraud_detector_node)
    builder.add_node("customer_support", customer_support_node)
    builder.add_node("compliance_judge", compliance_judge_node)
    builder.add_node("risk_judge", risk_judge_node)
    builder.add_node("synthesizer", synthesizer_node)
    builder.add_node("hitl", hitl_node)
    builder.add_node("response_publish", response_publish_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {w: w for w in WORKERS} | {"END": END},
    )
    for worker in WORKERS:
        builder.add_edge(worker, "supervisor")
    return builder.compile(checkpointer=saver, store=store)


def build_graph():
    conn = sqlite3.connect(str(CHECKPOINT_PATH), check_same_thread=False)
    return build_graph_with_backends(SqliteSaver(conn))


def load_customers() -> list[dict]:
    if not CUSTOMERS_PATH.exists():
        return []
    return list(json.loads(CUSTOMERS_PATH.read_text(encoding="utf-8")).get("customers") or [])


def load_alerts() -> list[dict]:
    if not ALERTS_PATH.exists():
        return []
    return list(json.loads(ALERTS_PATH.read_text(encoding="utf-8")).get("alerts") or [])


def get_customer(customer_id: str | None = None) -> dict:
    customers = load_customers()
    if not customers:
        return {
            "customer_id": "CUST-1001",
            "name": "Alex Rivera",
            "risk_tolerance": "moderate",
            "goals": ["retirement", "emergency_fund"],
        }
    if customer_id:
        for c in customers:
            if c.get("customer_id") == customer_id:
                return c
    return customers[0]


def get_alert(alert_id: str | None = None) -> dict:
    alerts = load_alerts()
    if not alerts:
        return {}
    if alert_id:
        for a in alerts:
            if a.get("alert_id") == alert_id:
                return a
    for a in alerts:
        if a.get("demo_gold") == "fraud":
            return a
    return alerts[0]


def make_initial_state(
    *,
    thread_id: str | None = None,
    query: str,
    customer_id: str | None = None,
    txn_alert: dict | None = None,
) -> SessionState:
    profile = get_customer(customer_id)
    cid = str(profile.get("customer_id") or customer_id or "CUST-1001")
    return {
        "thread_id": thread_id or str(uuid4()),
        "customer_id": cid,
        "query": query,
        "intent": None,
        "needs_graph": False,
        "needs_rag": True,
        "run_advisor": False,
        "run_fraud": False,
        "run_support": False,
        "goals": list(profile.get("goals") or []),
        "risk_tolerance": str(profile.get("risk_tolerance") or "moderate"),
        "txn_alert": txn_alert or {},
        "customer_profile": profile,
        "retrieved_chunks": [],
        "graph_paths": [],
        "advice_draft": None,
        "fraud_finding": None,
        "support_answer": None,
        "compliance_score": None,
        "risk_score": None,
        "risk_band": None,
        "final_response": None,
        "grounding_score": None,
        "revise_count": 0,
        "approval": "auto",
        "published": False,
        "step_log": [],
        "next": "END",
    }


DEMO_ADVICE_QUERY = (
    "I want personalized investment advice for retirement with moderate risk tolerance."
)


if __name__ == "__main__":
    from langgraph.types import Command

    graph = build_graph()
    state = make_initial_state(query=DEMO_ADVICE_QUERY, customer_id="CUST-1001")
    config = {"configurable": {"thread_id": state["thread_id"]}}
    print(f"AdviseGuard: {state['query']}\n")
    config = {**config, "recursion_limit": 60}
    for update in graph.stream(state, config, stream_mode="updates"):
        if not isinstance(update, dict):
            continue
        for node_name, node_update in update.items():
            if not isinstance(node_update, dict):
                print(f"  [{node_name}] interrupt/pause")
                continue
            if node_update.get("step_log"):
                print(f"  [{node_name}] {node_update['step_log'][-1]}")
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        print("\nHITL — auto-approving for CLI demo...")
        graph.invoke(Command(resume={"action": "approve"}), config)
    final = graph.get_state(config).values
    print(
        f"\nDone published={final.get('published')} intent={final.get('intent')} "
        f"band={final.get('risk_band')} approval={final.get('approval')}"
    )
