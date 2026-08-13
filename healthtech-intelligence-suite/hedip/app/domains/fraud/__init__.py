"""Fraud, waste & abuse thin domain."""

from __future__ import annotations

from app.rag.retrieval import hybrid_search
from app.state import HedipState
from app.tools.cases import load_case
from app.tools.neo4j_graph import graph_hops


def run_fraud(state: HedipState) -> dict:
    case_id = state.get("case_id") or "FRD-001"
    case = load_case("fraud", case_id)
    score = float(case.get("fraud_score") or 0.4)
    signals = case.get("signals") or []
    if case.get("community_anomaly"):
        signals.append("graph community anomaly")
        score = max(score, 0.82)
    if score >= 0.8:
        decision = "investigate"
    elif score >= 0.5:
        decision = "review"
    else:
        decision = "clear"
    evidence = hybrid_search("fraud waste abuse upcoding phantom billing", limit=3)
    graph = graph_hops(case_id) or graph_hops(str(case.get("provider_id") or "provider"))
    draft = (
        f"# Fraud Investigation Brief\n\n**Decision:** {decision}\n"
        f"**Score:** {score}\n**Signals:** {signals}\n\n"
        "Investigator copilot: review linked claims, addresses, and provider community."
    )
    return {
        "case_payload": case,
        "domain_result": {"stages": ["intake", "provider", "member", "graph", "score", "brief"]},
        "evidence": evidence,
        "graph_paths": graph,
        "citations": [{"id": "C1", "source": e.get("source"), "text": (e.get("text") or "")[:200]} for e in evidence[:3]],
        "recommendation": {"decision": decision, "fraud_score": score, "signals": signals},
        "draft": draft,
        "needs_hitl": decision == "investigate",
        "step_log": [f"Fraud: {case_id} decision={decision} score={score}"],
    }
