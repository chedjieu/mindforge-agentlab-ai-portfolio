"""Synthesizer — unified response pack + HITL decision."""

from __future__ import annotations

from app.guardrails import check_escalate_patterns, mask_pii
from app.state import SessionState


def _grounding(state: SessionState, citations: list[str]) -> float:
    chunks = {c.get("id") for c in (state.get("retrieved_chunks") or []) if c.get("id")}
    if not citations:
        return 0.55
    ok = len([x for x in citations if x in chunks]) / len(citations)
    score = 0.4 + 0.5 * ok
    if state.get("compliance_score") is not None:
        score += 0.1
    return round(min(1.0, score), 3)


def synthesizer_node(state: SessionState) -> dict:
    intent = state.get("intent") or "support"
    advice = state.get("advice_draft") or {}
    fraud = state.get("fraud_finding") or {}
    support = state.get("support_answer") or {}
    band = state.get("risk_band") or "low"
    compliance = float(state.get("compliance_score") or 0.0)

    parts = []
    citations: list[str] = []
    if advice and not advice.get("skipped"):
        parts.append(mask_pii(str(advice.get("summary") or "")))
        citations.extend(advice.get("citations") or [])
    if fraud and not fraud.get("skipped"):
        parts.append(mask_pii(str(fraud.get("summary") or "")))
        citations.extend(fraud.get("citations") or [])
    if support and not support.get("skipped"):
        parts.append(mask_pii(str(support.get("summary") or ""))[:400])
        citations.extend(support.get("citations") or [])

    # Dedupe citations
    seen = set()
    cites = []
    for c in citations:
        if c and c not in seen and c != "EMPTY":
            seen.add(c)
            cites.append(c)

    summary = " ".join(parts) if parts else "No actionable recommendation generated."
    grounding = _grounding(state, cites)

    # Revise only when grounding is weak (compliance/risk issues escalate to HITL instead)
    revise_count = int(state.get("revise_count") or 0)
    if grounding < 0.7 and revise_count < 2 and intent != "unknown":
        return {
            "final_response": None,
            "advice_draft": None if state.get("run_advisor") else state.get("advice_draft"),
            "fraud_finding": None if state.get("run_fraud") else state.get("fraud_finding"),
            "support_answer": None if state.get("run_support") else state.get("support_answer"),
            "compliance_score": None,
            "risk_score": None,
            "revise_count": revise_count + 1,
            "grounding_score": None,
            "step_log": state["step_log"]
            + [f"Synthesizer: revise #{revise_count + 1} grounding={grounding}"],
        }

    escalate = check_escalate_patterns(state.get("query") or "")
    force_hitl = (
        band in ("high", "critical")
        or bool(advice.get("high_stakes"))
        or (fraud.get("action") in ("escalate", "block"))
        or compliance < 0.6
        or grounding < 0.7
        or bool(escalate)
    )
    approval = "pending" if force_hitl else "auto"

    response = {
        "kind": intent,
        "summary": summary,
        "citations": cites,
        "advice": advice if not advice.get("skipped") else None,
        "fraud": fraud if not fraud.get("skipped") else None,
        "support": support if not support.get("skipped") else None,
        "risk_band": band,
        "risk_score": state.get("risk_score"),
        "compliance_score": compliance,
        "grounding_score": grounding,
        "graph_explanation": [p.get("explanation") for p in (state.get("graph_paths") or [])[:4]],
        "reasoning": f"Intent={intent}; compliance={compliance}; grounding={grounding}",
    }

    return {
        "final_response": response,
        "grounding_score": grounding,
        "approval": approval,
        "step_log": state["step_log"]
        + [f"Synthesizer: approval={approval} grounding={grounding} band={band}"],
    }
