"""HITL node — clinician approve / edit / reject via interrupt."""

from __future__ import annotations

from langgraph.types import interrupt

from app.memory.semantic import save_semantic_feedback
from app.state import TreatmentPlanState


def hitl_node(state: TreatmentPlanState) -> dict:
    payload = {
        "draft_plan": state.get("draft_plan"),
        "safety_score": state.get("safety_score"),
        "medication_review": state.get("medication_review"),
        "citations": state.get("citations"),
        "patient_id": state.get("patient_id"),
        "judge_feedback": state.get("judge_feedback"),
    }
    decision = interrupt(payload)
    # decision expected: {"action": "approve"|"edit"|"reject", "edited_body": optional}
    if not isinstance(decision, dict):
        decision = {"action": "approve"}

    action = str(decision.get("action") or "approve").lower()
    if action == "reject":
        return {
            "approval": "rejected",
            "final_plan": "Plan rejected by clinician.",
            "published": False,
            "step_log": ["HITL: rejected"],
        }

    if action == "edit":
        edited = decision.get("edited_body") or state.get("draft_plan") or ""
        patient_id = str(state.get("patient_id") or "unknown")
        save_semantic_feedback(patient_id, {"type": "clinician_edit", "text": edited[:2000]})
        return {
            "approval": "edited",
            "draft_plan": edited,
            "final_plan": edited,
            "step_log": ["HITL: edited and approved"],
        }

    plan = state.get("draft_plan") or ""
    return {
        "approval": "approved",
        "final_plan": plan,
        "step_log": ["HITL: approved"],
    }
