"""Compliance judge — regulatory / ethical gate."""

from __future__ import annotations

from app.guardrails import check_escalate_patterns
from app.state import SessionState


def compliance_judge_node(state: SessionState) -> dict:
    advice = state.get("advice_draft") or {}
    fraud = state.get("fraud_finding") or {}
    support = state.get("support_answer") or {}
    query = state.get("query") or ""
    chunks = state.get("retrieved_chunks") or []

    score = 0.55
    flags: list[str] = []
    if any(c.get("metadata", {}).get("domain") == "regulations" for c in chunks):
        score += 0.2
    if advice.get("disclaimer"):
        score += 0.1
    if advice.get("citations") or support.get("citations") or fraud.get("citations"):
        score += 0.1
    # Prohibited marketing language (ignore educational disclaimers)
    blob = f"{advice.get('summary', '')} {query}".lower()
    if "risk-free" in blob or "guaranteed return" in blob or "guarantee returns" in blob:
        flags.append("prohibited_guarantee_language")
        score -= 0.4
    elif "guaranteed" in blob and "not a guarantee" not in blob and "do not" not in blob:
        flags.append("prohibited_guarantee_language")
        score -= 0.4
    flags.extend(f"escalate:{p}" for p in check_escalate_patterns(query))
    if flags:
        score -= 0.1 * len(flags)
    score = round(max(0.0, min(1.0, score)), 3)

    # Force revise path via clearing final_response later if needed — score only here
    return {
        "compliance_score": score,
        "step_log": state["step_log"]
        + [f"ComplianceJudge: score={score} flags={flags}"],
    }
