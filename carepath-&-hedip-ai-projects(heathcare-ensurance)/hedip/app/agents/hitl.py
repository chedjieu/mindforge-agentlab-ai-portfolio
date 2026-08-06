"""HITL interrupt."""

from __future__ import annotations

from langgraph.types import interrupt

from app.memory.semantic import save_semantic
from app.state import HedipState


def hitl_node(state: HedipState) -> dict:
    payload = {
        "domain": state.get("domain"),
        "draft": state.get("draft"),
        "recommendation": state.get("recommendation"),
        "safety_score": state.get("safety_score"),
        "citations": state.get("citations"),
        "case_id": state.get("case_id"),
    }
    decision = interrupt(payload)
    if not isinstance(decision, dict):
        decision = {"action": "approve"}
    action = str(decision.get("action") or "approve").lower()
    if action == "reject":
        return {
            "approval": "rejected",
            "final_response": "Decision rejected by reviewer.",
            "published": False,
            "step_log": ["HITL: rejected"],
        }
    if action == "edit":
        edited = decision.get("edited_body") or state.get("draft") or ""
        save_semantic(str(state.get("case_id") or state.get("domain")), {"type": "edit", "text": edited[:2000]})
        return {
            "approval": "edited",
            "draft": edited,
            "final_response": edited,
            "step_log": ["HITL: edited"],
        }
    return {
        "approval": "approved",
        "final_response": state.get("draft") or json_dump(state.get("recommendation")),
        "step_log": ["HITL: approved"],
    }


def json_dump(obj) -> str:
    import json

    return json.dumps(obj or {}, default=str, indent=2)
