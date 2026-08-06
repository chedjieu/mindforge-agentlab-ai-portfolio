"""Supervisor — routes treatment-plan workflow (pure logic, no LLM)."""

from __future__ import annotations

from app.state import Route, TreatmentPlanState


def supervisor_node(state: TreatmentPlanState) -> dict:
    nxt: Route = "END"

    if state.get("blocked"):
        nxt = "plan_publish"
    elif state.get("approval") == "rejected":
        nxt = "END"
    elif state.get("patient_profile") is None:
        nxt = "patient_data_extractor"
    elif state.get("medication_review") is None:
        nxt = "medication_interaction_checker"
    elif state.get("draft_plan") is None:
        nxt = "treatment_plan_generator"
    elif state.get("patient_preferences") and not state.get("preferences_applied"):
        nxt = "patient_preference_agent"
    elif state.get("safety_score") is None:
        nxt = "treatment_plan_evaluator"
    elif state.get("needs_revise") and int(state.get("revise_count") or 0) < 2:
        nxt = "treatment_plan_generator"
    elif state.get("approval") == "pending":
        nxt = "hitl"
    elif state.get("approval") in ("approved", "edited", "auto") and not state.get("published"):
        nxt = "plan_publish"
    else:
        nxt = "END"

    return {
        "next": nxt,
        "step_log": [f"Supervisor: route -> {nxt}"],
    }
