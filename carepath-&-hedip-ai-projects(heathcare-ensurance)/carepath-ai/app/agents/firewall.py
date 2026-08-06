"""Firewall node — hard-block injection / clinical-safety bypass."""

from __future__ import annotations

from app.guardrails import check_escalate_patterns, check_query_guardrail
from app.state import TreatmentPlanState


def firewall_node(state: TreatmentPlanState) -> dict:
    text = " ".join(
        [
            state.get("query") or "",
            str(state.get("patient_preferences") or ""),
        ]
    )
    refusal = check_query_guardrail(text)
    if refusal:
        return {
            "blocked": True,
            "block_reason": refusal,
            "final_plan": refusal,
            "approval": "rejected",
            "published": False,
            "step_log": [f"Firewall: BLOCKED ({refusal[:80]}...)"],
        }

    escalations = check_escalate_patterns(text)
    log = ["Firewall: pass"]
    if escalations:
        log.append(f"Firewall: escalate markers {escalations} — HITL required")
    return {
        "blocked": False,
        "step_log": log,
    }
