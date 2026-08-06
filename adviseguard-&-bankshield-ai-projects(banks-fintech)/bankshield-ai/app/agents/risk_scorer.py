"""Risk scoring — fuse ML stub, graph, behavioral, regulatory severity."""

from __future__ import annotations

from app.state import InvestigationState, RiskBand


def _band(score: float) -> RiskBand:
    if score >= 0.85:
        return "critical"
    if score >= 0.65:
        return "high"
    if score >= 0.4:
        return "medium"
    return "low"


def risk_scorer_node(state: InvestigationState) -> dict:
    txn = state.get("txn_features") or {}
    identity = state.get("identity_findings") or []
    graph_paths = state.get("graph_paths") or []
    fraud_types = set(state.get("fraud_types") or [])
    alert = state.get("alert") or {}

    ml_stub = float(alert.get("ml_score") or txn.get("txn_risk_score") or 0.3)
    txn_score = float(txn.get("txn_risk_score") or 0.0)
    behavior = float(txn.get("behavior_anomaly") or alert.get("behavior_anomaly") or 0.0)

    synthetic = 0.0
    ofac = False
    for f in identity:
        if f.get("type") == "kyc":
            synthetic = float(f.get("synthetic_risk") or 0.0)
        if f.get("type") == "sanctions_screen" and f.get("ofac_match"):
            ofac = True

    mule_bonus = 0.0
    for e in state.get("evidence") or []:
        if e.get("source") == "graph_walker":
            mule = e.get("mule") or {}
            if mule.get("is_mule_suspect"):
                mule_bonus = float(mule.get("mule_score") or 0.5)
            break

    graph_density = min(0.3, 0.05 * max(0, len(graph_paths) - 1))
    reg_severity = 0.35 if ofac or ("sanctions" in fraud_types) else (
        0.25 if fraud_types & {"aml", "wire", "mule"} else 0.1
    )

    score = (
        0.25 * ml_stub
        + 0.20 * txn_score
        + 0.15 * behavior
        + 0.15 * synthetic
        + 0.15 * mule_bonus
        + graph_density
        + reg_severity * 0.5
    )
    if ofac:
        score = max(score, 0.9)
    score = round(min(1.0, score), 3)
    band = _band(score)

    # High-risk types always at least high
    if fraud_types & {"wire", "sanctions", "aml", "mule"} and band == "low":
        band = "medium"
        score = max(score, 0.45)

    return {
        "risk_score": score,
        "risk_band": band,
        "step_log": state["step_log"]
        + [
            f"RiskScorer: score={score} band={band} ofac={ofac} mule={mule_bonus:.2f}"
        ],
    }
