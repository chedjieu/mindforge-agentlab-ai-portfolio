"""Plan publish — audit log + mock EHR write."""

from __future__ import annotations

from app.state import TreatmentPlanState
from app.tools.publish_plan import publish_plan_record


def plan_publish(state: TreatmentPlanState) -> dict:
    if state.get("blocked"):
        return {
            "published": True,
            "final_plan": state.get("final_plan") or state.get("block_reason") or "Blocked",
            "step_log": ["Publish: blocked request logged"],
        }

    if state.get("approval") == "rejected":
        return {
            "published": False,
            "step_log": ["Publish: skipped (rejected)"],
        }

    plan = state.get("final_plan") or state.get("draft_plan") or ""
    record = publish_plan_record(
        {
            "thread_id": state.get("thread_id"),
            "patient_id": state.get("patient_id"),
            "clinician_id": state.get("clinician_id"),
            "approval": state.get("approval"),
            "safety_score": state.get("safety_score"),
            "medication_summary": (state.get("medication_review") or {}).get("summary"),
            "citations": state.get("citations") or [],
            "plan": plan,
        }
    )
    return {
        "published": True,
        "final_plan": plan,
        "step_log": [f"Publish: wrote audit id={record.get('id')}"],
    }
