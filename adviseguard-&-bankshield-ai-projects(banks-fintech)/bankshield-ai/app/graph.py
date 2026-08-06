"""BankShield LangGraph — supervisor routes investigation workers in a loop."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore

from app.agents.graph_walker import graph_walker_node
from app.agents.grounder_judge import grounder_judge_node
from app.agents.hitl import hitl_node
from app.agents.identity_kyc import identity_kyc_node
from app.agents.recommender import recommender_node
from app.agents.regulatory_rag import regulatory_rag_node
from app.agents.risk_scorer import risk_scorer_node
from app.agents.sar_publisher import sar_publisher_node
from app.agents.similar_cases import similar_cases_node
from app.agents.supervisor import supervisor_node
from app.agents.transaction_intel import transaction_intel_node
from app.agents.triage_router import triage_router_node
from app.state import InvestigationState

CHECKPOINT_PATH = Path(__file__).resolve().parent.parent / "checkpoints.sqlite"
ALERTS_PATH = Path(__file__).resolve().parent.parent / "data" / "alerts" / "alerts.json"

WORKERS = (
    "triage_router",
    "identity_kyc",
    "transaction_intel",
    "graph_walker",
    "regulatory_rag",
    "similar_case_retriever",
    "risk_scorer",
    "recommender",
    "grounder_judge",
    "hitl",
    "sar_publisher",
)


def build_graph_with_backends(saver: Any, store: BaseStore | None = None):
    builder = StateGraph(InvestigationState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("triage_router", triage_router_node)
    builder.add_node("identity_kyc", identity_kyc_node)
    builder.add_node("transaction_intel", transaction_intel_node)
    builder.add_node("graph_walker", graph_walker_node)
    builder.add_node("regulatory_rag", regulatory_rag_node)
    builder.add_node("similar_case_retriever", similar_cases_node)
    builder.add_node("risk_scorer", risk_scorer_node)
    builder.add_node("recommender", recommender_node)
    builder.add_node("grounder_judge", grounder_judge_node)
    builder.add_node("hitl", hitl_node)
    builder.add_node("sar_publisher", sar_publisher_node)

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


def load_alerts() -> list[dict]:
    if not ALERTS_PATH.exists():
        return []
    data = json.loads(ALERTS_PATH.read_text(encoding="utf-8"))
    return list(data.get("alerts") or [])


def get_alert(alert_id: str | None = None) -> dict:
    alerts = load_alerts()
    if not alerts:
        return {
            "alert_id": "ALT-DEMO-001",
            "alert_type": "wire_mule",
            "description": "High-value wire with shared device mule indicators",
            "customer_id": "CUST-1001",
            "payment_rail": "wire",
            "amount": 48500,
            "fraud_types": ["wire", "mule"],
            "needs_graph": True,
        }
    if alert_id:
        for a in alerts:
            if a.get("alert_id") == alert_id:
                return a
    # Prefer gold mule demo
    for a in alerts:
        if a.get("demo_gold") == "mule":
            return a
    return alerts[0]


def make_initial_state(
    *,
    thread_id: str | None = None,
    alert: dict | None = None,
    query: str | None = None,
    investigator_id: str = "inv-demo",
) -> InvestigationState:
    alert = alert or get_alert()
    tid = thread_id or str(uuid4())
    case_id = str(alert.get("case_id") or alert.get("alert_id") or tid)
    q = query or str(alert.get("description") or f"Investigate alert {case_id}")
    return {
        "thread_id": tid,
        "case_id": case_id,
        "investigator_id": investigator_id,
        "alert": alert,
        "query": q,
        "fraud_types": None,
        "payment_rail": None,
        "needs_graph": bool(alert.get("needs_graph", False)),
        "needs_identity": True,
        "sensitivity": "normal",
        "entities": {},
        "identity_findings": [],
        "txn_features": None,
        "evidence": [],
        "graph_paths": [],
        "reg_citations": [],
        "similar_cases": [],
        "risk_score": None,
        "risk_band": None,
        "recommendation": None,
        "grounding_score": None,
        "revise_count": 0,
        "approval": "auto",
        "sar_draft": None,
        "published": False,
        "step_log": [],
        "next": "END",
    }


DEMO_ALERT_ID = "ALT-MULE-001"


if __name__ == "__main__":
    from langgraph.types import Command

    graph = build_graph()
    state = make_initial_state(alert=get_alert(DEMO_ALERT_ID))
    config = {"configurable": {"thread_id": state["thread_id"]}}

    print(f"Investigating {state['case_id']}: {state['query']}\n")
    for update in graph.stream(state, config, stream_mode="updates"):
        if not isinstance(update, dict):
            continue
        for node_name, node_update in update.items():
            if not isinstance(node_update, dict):
                print(f"  [{node_name}] interrupt/pause")
                continue
            if node_update.get("step_log"):
                print(f"  [{node_name}] {node_update['step_log'][-1]}")
            if node_update.get("next"):
                print(f"  [{node_name}] next={node_update['next']}")

    snap = graph.get_state(config)
    pending = any(intr for task in snap.tasks for intr in task.interrupts)
    if pending:
        print("\nHITL interrupt — auto-approving for CLI demo...")
        graph.invoke(Command(resume={"action": "approve"}), config)

    final = graph.get_state(config).values
    print(
        f"\nDone — published={final.get('published')} "
        f"risk={final.get('risk_band')} ({final.get('risk_score')}) "
        f"approval={final.get('approval')} grounding={final.get('grounding_score')}"
    )
    print(f"Total steps: {len(final.get('step_log') or [])}")
