"""Risk assessment judge — may force HITL."""

from __future__ import annotations

from app.state import RiskBand, SessionState


def _band(score: float) -> RiskBand:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def risk_judge_node(state: SessionState) -> dict:
    fraud = state.get("fraud_finding") or {}
    advice = state.get("advice_draft") or {}
    compliance = float(state.get("compliance_score") or 0.5)

    fraud_score = float(fraud.get("txn_risk_score") or 0.0)
    advice_risk = 0.55 if advice.get("high_stakes") else 0.25
    if str(advice.get("risk_tolerance")) == "aggressive":
        advice_risk = max(advice_risk, 0.6)

    score = max(fraud_score, advice_risk * (1.1 - compliance * 0.3))
    if compliance < 0.5:
        score = max(score, 0.7)
    score = round(min(1.0, score), 3)
    band = _band(score)
    if fraud.get("risk_band") in ("high", "critical"):
        band = fraud["risk_band"]  # type: ignore[assignment]
        score = max(score, float(fraud_score))

    return {
        "risk_score": score,
        "risk_band": band,
        "step_log": state["step_log"] + [f"RiskJudge: score={score} band={band}"],
    }
