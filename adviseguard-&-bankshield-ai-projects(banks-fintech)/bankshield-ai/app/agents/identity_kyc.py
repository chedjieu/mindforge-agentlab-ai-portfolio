"""Identity / KYC verification worker."""

from __future__ import annotations

from app.state import InvestigationState
from app.tools.kyc_mock import check_sanctions, verify_identity


def identity_kyc_node(state: InvestigationState) -> dict:
    alert = state.get("alert") or {}
    entities = state.get("entities") or {}
    customer_id = entities.get("customer_id") or alert.get("customer_id") or "UNKNOWN"
    kyc = verify_identity(str(customer_id))
    name = kyc.get("name") or entities.get("beneficiary_name") or alert.get("customer_name") or ""
    sanctions = check_sanctions(str(name), alert.get("beneficiary_country"))

    findings = [
        {
            "type": "kyc",
            "customer_id": customer_id,
            "kyc_status": kyc.get("kyc_status"),
            "synthetic_risk": kyc.get("synthetic_risk"),
            "face_match": kyc.get("face_match"),
            "details": kyc.get("findings") or [],
        },
        {
            "type": "sanctions_screen",
            "name": name,
            "ofac_match": sanctions.get("ofac_match"),
            "matched_entry": sanctions.get("matched_entry"),
            "confidence": sanctions.get("confidence"),
        },
    ]
    evidence = list(state.get("evidence") or [])
    evidence.append(
        {
            "id": f"kyc-{customer_id}",
            "source": "identity_kyc",
            "summary": f"KYC={kyc.get('kyc_status')} synthetic={kyc.get('synthetic_risk')} "
            f"OFAC={sanctions.get('ofac_match')}",
        }
    )
    # Force graph when OFAC hit
    needs_graph = state.get("needs_graph") or bool(sanctions.get("ofac_match"))
    fraud_types = list(state.get("fraud_types") or [])
    if sanctions.get("ofac_match") and "sanctions" not in fraud_types:
        fraud_types.append("sanctions")

    return {
        "identity_findings": findings,
        "evidence": evidence,
        "needs_graph": needs_graph,
        "fraud_types": fraud_types,
        "sensitivity": "sensitive"
        if sanctions.get("ofac_match") or float(kyc.get("synthetic_risk") or 0) >= 0.6
        else state.get("sensitivity", "normal"),
        "step_log": state["step_log"]
        + [
            f"Identity: kyc={kyc.get('kyc_status')} ofac={sanctions.get('ofac_match')} "
            f"synthetic={kyc.get('synthetic_risk')}"
        ],
    }
