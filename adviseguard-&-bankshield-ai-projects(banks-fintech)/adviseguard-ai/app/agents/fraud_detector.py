"""Fraud detection specialist."""

from __future__ import annotations

from app.state import SessionState
from app.tools.txn_monitor import analyze_transaction


def fraud_detector_node(state: SessionState) -> dict:
    alert = state.get("txn_alert") or {}
    if not alert:
        # Soft fraud screen from query alone
        alert = {
            "amount": 0,
            "payment_rail": "unknown",
            "description": state.get("query") or "",
            "avg_amount_30d": 1,
        }
    features = analyze_transaction(alert)
    graph = state.get("graph_paths") or {}
    shared = sum(
        1
        for p in (state.get("graph_paths") or [])
        for r in p.get("relationships") or []
        if r in ("SHARES_DEVICE", "MATCHES_PATTERN", "TRANSFERRED_TO")
    )
    score = float(features["txn_risk_score"])
    if shared >= 2:
        score = min(1.0, score + 0.2)
    band = features["risk_band"]
    if score >= 0.85:
        band = "critical"
    elif score >= 0.65:
        band = "high"
    elif score >= 0.4:
        band = "medium"
    else:
        band = "low"

    finding = {
        "alert_id": alert.get("alert_id"),
        "anomalies": features.get("anomalies") or [],
        "txn_risk_score": round(score, 3),
        "risk_band": band,
        "graph_shared_signals": shared,
        "summary": (
            f"Fraud screen band={band} score={score:.2f} "
            f"anomalies={features.get('anomalies')} shared_signals={shared}"
        ),
        "citations": [
            c.get("id")
            for c in (state.get("retrieved_chunks") or [])
            if c.get("metadata", {}).get("domain") in ("fraud_patterns", "regulations", None)
        ][:5],
        "action": "escalate" if band in ("high", "critical") else "monitor" if band == "medium" else "clear",
    }
    return {
        "fraud_finding": finding,
        "step_log": state["step_log"]
        + [f"FraudDetector: band={band} score={score:.2f} action={finding['action']}"],
    }
