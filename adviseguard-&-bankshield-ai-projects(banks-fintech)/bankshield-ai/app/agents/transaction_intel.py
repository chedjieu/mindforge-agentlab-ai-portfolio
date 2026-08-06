"""Transaction intelligence worker (includes behavioral stub)."""

from __future__ import annotations

from app.state import InvestigationState
from app.tools.txn_features import extract_txn_features


def transaction_intel_node(state: InvestigationState) -> dict:
    alert = state.get("alert") or {}
    features = extract_txn_features(alert)
    evidence = list(state.get("evidence") or [])
    evidence.append(
        {
            "id": f"txn-{alert.get('alert_id', state.get('case_id'))}",
            "source": "transaction_intel",
            "summary": (
                f"rail={features['payment_rail']} amount={features['amount']} "
                f"anomalies={features['anomalies']} score={features['txn_risk_score']}"
            ),
            "features": features,
        }
    )
    # Empty-sentinel pattern: always set txn_features (even if sparse)
    if not features:
        features = {"txn_risk_score": 0.0, "anomalies": [], "payment_rail": "unknown"}

    needs_graph = state.get("needs_graph") or any(
        a.startswith("velocity") or a == "new_beneficiary" for a in features.get("anomalies", [])
    )
    return {
        "txn_features": features,
        "evidence": evidence,
        "needs_graph": bool(needs_graph),
        "step_log": state["step_log"]
        + [f"TxnIntel: score={features['txn_risk_score']} anomalies={features['anomalies']}"],
    }
