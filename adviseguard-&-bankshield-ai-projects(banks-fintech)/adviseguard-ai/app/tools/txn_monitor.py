"""Transaction anomaly features for fraud detection."""

from __future__ import annotations

from typing import Any

HIGH_RISK_COUNTRIES = {"KP", "IR", "SY", "CU", "RU"}


def analyze_transaction(alert: dict[str, Any]) -> dict[str, Any]:
    amount = float(alert.get("amount") or 0)
    rail = str(alert.get("payment_rail") or "unknown").lower()
    country = str(alert.get("beneficiary_country") or "").upper()
    velocity_1h = int(alert.get("velocity_1h") or 0)
    avg = float(alert.get("avg_amount_30d") or max(amount * 0.1, 1.0))
    z = (amount - avg) / max(avg, 1.0)
    anomalies: list[str] = []
    score = 0.1
    if amount >= 10000 and rail in ("wire", "ach", "rtp", "fednow"):
        anomalies.append("high_value_transfer")
        score += 0.25
    if velocity_1h >= 3:
        anomalies.append("velocity_burst")
        score += 0.25
    if z >= 5:
        anomalies.append("amount_anomaly")
        score += 0.2
    if country in HIGH_RISK_COUNTRIES:
        anomalies.append(f"high_risk_country:{country}")
        score += 0.25
    if alert.get("new_beneficiary"):
        anomalies.append("new_beneficiary")
        score += 0.15
    if float(alert.get("behavior_anomaly") or 0) >= 0.6:
        anomalies.append("behavior_shift")
        score += 0.15
    score = min(1.0, score)
    band = (
        "critical"
        if score >= 0.85
        else "high"
        if score >= 0.65
        else "medium"
        if score >= 0.4
        else "low"
    )
    return {
        "amount": amount,
        "payment_rail": rail,
        "anomalies": anomalies,
        "txn_risk_score": round(score, 3),
        "risk_band": band,
        "amount_zscore_proxy": round(z, 3),
    }
