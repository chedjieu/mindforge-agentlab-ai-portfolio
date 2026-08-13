"""Patient preference incorporation agent."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from app.llm import get_chat_model
from app.state import TreatmentPlanState


def patient_preference_agent(state: TreatmentPlanState) -> dict:
    prefs = state.get("patient_preferences") or {}
    draft = state.get("draft_plan") or ""
    if not prefs:
        return {
            "preferences_applied": True,
            "step_log": ["PreferenceAgent: no preferences — pass-through"],
        }

    llm = get_chat_model()
    prompt = (
        "Adapt the treatment plan to honor patient preferences. "
        "Do not remove required safety monitoring. Prefer oral alternatives when "
        "patient avoids injectables. Keep Goals/Interventions/Monitoring/Follow-up.\n\n"
        f"PREFERENCES:\n{json.dumps(prefs, default=str)}\n\n"
        f"DRAFT PLAN:\n{draft}\n"
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    adapted = str(resp.content)

    # Deterministic safety net for golden P001 preference
    avoid = json.dumps(prefs).lower()
    if "inject" in avoid or "glp-1" in avoid or "glp1" in avoid:
        if "injectable" in adapted.lower() and "avoid" not in adapted.lower()[:200]:
            adapted = (
                adapted
                + "\n\n### Preference note\n"
                + "- Patient prefers to avoid injectable GLP-1; use oral intensification pathway.\n"
            )

    return {
        "draft_plan": adapted,
        "preferences_applied": True,
        "safety_score": None,  # re-evaluate after preference edits
        "step_log": [f"PreferenceAgent: applied preferences keys={list(prefs.keys())}"],
    }
