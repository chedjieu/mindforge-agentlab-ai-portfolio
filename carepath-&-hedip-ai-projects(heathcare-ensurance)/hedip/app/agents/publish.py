"""Publish node."""

from __future__ import annotations

import json

from app.memory.episodic import append_episodic
from app.state import HedipState
from app.tools.publish import publish_decision


def publish_node(state: HedipState) -> dict:
    if state.get("blocked"):
        return {
            "published": True,
            "final_response": state.get("final_response") or state.get("block_reason") or "Blocked",
            "step_log": ["Publish: blocked logged"],
        }
    if state.get("approval") == "rejected":
        return {"published": False, "step_log": ["Publish: skipped rejected"]}

    # auto-approve non-HITL
    approval = state.get("approval")
    if approval == "auto" or (not state.get("needs_hitl") and approval == "pending"):
        approval = "auto"

    body = state.get("final_response") or state.get("draft") or json.dumps(state.get("recommendation") or {}, default=str)
    record = publish_decision(
        {
            "thread_id": state.get("thread_id"),
            "domain": state.get("domain"),
            "case_id": state.get("case_id"),
            "approval": approval,
            "safety_score": state.get("safety_score"),
            "recommendation": state.get("recommendation"),
            "body": body,
        }
    )
    append_episodic(
        str(state.get("domain") or "unknown"),
        {
            "case_id": state.get("case_id"),
            "decision": (state.get("recommendation") or {}).get("decision"),
            "approval": approval,
            "publish_id": record.get("id"),
        },
    )
    return {
        "published": True,
        "approval": approval if approval != "pending" else "auto",
        "final_response": body,
        "step_log": [f"Publish: {record.get('id')}"],
    }
