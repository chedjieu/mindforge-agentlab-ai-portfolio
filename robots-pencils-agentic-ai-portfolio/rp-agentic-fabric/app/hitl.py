"""Human-in-the-loop approval node."""

from __future__ import annotations

from datetime import datetime, timezone

from langgraph.types import interrupt

from app.hitl_log import append_hitl_outcome
from app.state import Approval, EngagementState


def hitl_node(state: EngagementState) -> dict:
    """Pause for human approval; resume with action approve/edit/reject."""
    queued_at = datetime.now(timezone.utc)
    payload = interrupt(
        {
            "draft_plan": state["draft_plan"],
            "vertical": state["vertical"],
            "tenant_id": state["tenant_id"],
            "judge_scores": state["judge_scores"],
            "reuse_decisions": state["reuse_decisions"],
            "policy_pack_id": state["policy_pack_id"],
            "raw_brief": state["raw_brief"],
            "queued_at": queued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    decided_at = datetime.now(timezone.utc)
    latency_s = max(0.0, (decided_at - queued_at).total_seconds())

    action = str(payload.get("action", "approve")).lower()
    edited_body = payload.get("edited_body")
    draft_before = dict(state["draft_plan"]) if state["draft_plan"] else {}
    draft = dict(draft_before)

    approval: Approval
    if action == "approve":
        approval = "approved"
        log = "HITL: approved"
    elif action == "edit":
        approval = "edited"
        if edited_body:
            draft["summary"] = str(edited_body)
        log = "HITL: edited and approved"
    else:
        approval = "rejected"
        log = "HITL: rejected"

    try:
        append_hitl_outcome(
            {
                "engagement_id": state.get("engagement_id"),
                "tenant_id": state.get("tenant_id"),
                "vertical": state.get("vertical"),
                "action": action,
                "approval": approval,
                "judge_scores": state.get("judge_scores"),
                "draft_before": draft_before.get("summary"),
                "draft_after": draft.get("summary"),
                "queued_at": queued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "hitl_latency_seconds": round(latency_s, 3),
            }
        )
    except Exception:
        pass

    return {
        "approval": approval,
        "draft_plan": draft,
        "step_log": state["step_log"] + [log],
    }
