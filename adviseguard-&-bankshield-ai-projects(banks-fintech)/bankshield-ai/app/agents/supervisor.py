"""Supervisor — routes investigation steps (pure logic, no LLM)."""

from __future__ import annotations

from app.state import InvestigationState, Route


def supervisor_node(state: InvestigationState) -> dict:
    nxt: Route = "END"

    if state["approval"] == "rejected":
        nxt = "END"
    elif state["fraud_types"] is None:
        nxt = "triage_router"
    elif state["needs_identity"] and not state["identity_findings"]:
        nxt = "identity_kyc"
    elif state["txn_features"] is None:
        nxt = "transaction_intel"
    elif state["needs_graph"] and state["graph_paths"] == []:
        nxt = "graph_walker"
    elif state["reg_citations"] == []:
        nxt = "regulatory_rag"
    elif state["similar_cases"] == []:
        nxt = "similar_case_retriever"
    elif state["risk_score"] is None:
        nxt = "risk_scorer"
    elif state["recommendation"] is None:
        nxt = "recommender"
    elif state["grounding_score"] is None:
        nxt = "grounder_judge"
    elif state["approval"] == "pending":
        nxt = "hitl"
    elif state["approval"] in ("approved", "edited", "auto") and not state["published"]:
        nxt = "sar_publisher"
    else:
        nxt = "END"

    return {
        "next": nxt,
        "step_log": state["step_log"] + [f"Supervisor: route -> {nxt}"],
    }
