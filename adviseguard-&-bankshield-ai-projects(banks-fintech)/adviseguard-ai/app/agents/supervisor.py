"""Supervisor — pure routing logic (no LLM)."""

from __future__ import annotations

from app.state import Route, SessionState


def supervisor_node(state: SessionState) -> dict:
    nxt: Route = "END"

    if state["approval"] == "rejected":
        nxt = "END"
    elif state["intent"] is None:
        nxt = "intent_router"
    elif state["needs_rag"] and state["retrieved_chunks"] == []:
        nxt = "hybrid_retriever"
    elif state["needs_graph"] and state["graph_paths"] == []:
        nxt = "graph_walker"
    elif state["run_advisor"] and state["advice_draft"] is None:
        nxt = "financial_advisor"
    elif state["run_fraud"] and state["fraud_finding"] is None:
        nxt = "fraud_detector"
    elif state["run_support"] and state["support_answer"] is None:
        nxt = "customer_support"
    elif state["compliance_score"] is None:
        nxt = "compliance_judge"
    elif state["risk_score"] is None:
        nxt = "risk_judge"
    elif state["final_response"] is None:
        nxt = "synthesizer"
    elif state["approval"] == "pending":
        nxt = "hitl"
    elif state["approval"] in ("approved", "edited", "auto") and not state["published"]:
        nxt = "response_publish"
    else:
        nxt = "END"

    return {
        "next": nxt,
        "step_log": state["step_log"] + [f"Supervisor: route -> {nxt}"],
    }
