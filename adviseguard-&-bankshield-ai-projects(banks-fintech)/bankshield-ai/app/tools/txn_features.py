"""Transaction intelligence feature extraction (deep for wire/ACH)."""

from __future__ import annotations

from typing import Any

HIGH_RISK_COUNTRIES = {"KP", "IR", "SY", "CU", "RU", "MM"}


def extract_txn_features(alert: dict[str, Any]) -> dict[str, Any]:
    amount = float(alert.get("amount") or 0)
    rail = str(alert.get("payment_rail") or alert.get("channel") or "unknown").lower()
    country = str(alert.get("beneficiary_country") or alert.get("country") or "").upper()
    velocity_1h = int(alert.get("velocity_1h") or 0)
    velocity_24h = int(alert.get("velocity_24h") or 0)
    avg_amount_30d = float(alert.get("avg_amount_30d") or max(amount * 0.1, 1.0))
    amount_z = (amount - avg_amount_30d) / max(avg_amount_30d, 1.0)

    anomalies: list[str] = []
    score = 0.1

    if rail in ("wire", "ach", "rtp", "fednow") and amount >= 10000:
        anomalies.append("high_value_transfer")
        score += 0.2
    if velocity_1h >= 3:
        anomalies.append("velocity_burst_1h")
        score += 0.25
    if velocity_24h >= 8:
        anomalies.append("velocity_burst_24h")
        score += 0.15
    if amount_z >= 5:
        anomalies.append("amount_anomaly_vs_history")
        score += 0.2
    if country in HIGH_RISK_COUNTRIES:
        anomalies.append(f"high_risk_country:{country}")
        score += 0.25
    if alert.get("new_beneficiary"):
        anomalies.append("new_beneficiary")
        score += 0.15
    if alert.get("night_owl"):
        anomalies.append("unusual_hour")
        score += 0.1
    if rail in ("rtp", "fednow") and amount >= 2500:
        anomalies.append("instant_rail_elevated")
        score += 0.1

    # Behavioral stub folded into txn intel for v1
    behavior_delta = float(alert.get("behavior_anomaly") or 0.0)
    if behavior_delta >= 0.6:
        anomalies.append("behavior_embedding_shift")
        score += 0.15

    return {
        "amount": amount,
        "payment_rail": rail,
        "beneficiary_country": country or None,
        "velocity_1h": velocity_1h,
        "velocity_24h": velocity_24h,
        "amount_zscore_proxy": round(amount_z, 3),
        "anomalies": anomalies,
        "txn_risk_score": round(min(1.0, score), 3),
        "behavior_anomaly": behavior_delta,
    }
