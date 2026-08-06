"""Supervisor — routes engagements to the next worker."""

from __future__ import annotations

from app.state import EngagementState, Route


def _needs_hitl(state: EngagementState) -> bool:
    vertical = state.get("vertical")
    scores = state.get("judge_scores") or {}
    cfg = state.get("guardrail_config") or {}
    if cfg.get("hitl_required"):
        return True
    if vertical in ("healthcare", "finserv"):
        return True
    if scores and not scores.get("pass", True):
        return True
    draft = state.get("draft_plan") or {}
    if draft.get("recommended_action") == "escalate":
        return True
    if draft.get("risk_flags"):
        return True
    return False


def supervisor_node(state: EngagementState) -> dict:
    """Decide the next node based on current engagement progress."""
    nxt: Route = "END"

    if state["approval"] == "rejected":
        nxt = "END"
    elif state["vertical"] is None:
        nxt = "vertical_router"
    elif state["guardrail_config"] is None:
        nxt = "compliance_mapper"
    elif not state["reuse_decided"]:
        nxt = "reuse_broker"
    elif state["evidence"] == []:
        nxt = "retrieval"
    elif state["draft_plan"] is None:
        nxt = "engagement_synthesizer"
    elif state["judge_scores"] is None:
        nxt = "judge_gate"
    elif state["approval"] == "pending" and _needs_hitl(state):
        nxt = "hitl"
    elif state["approval"] in ("approved", "edited", "auto") and not state["published"]:
        nxt = "audit_publish"
    elif state["approval"] == "pending" and not _needs_hitl(state) and not state["published"]:
        # Auto-approve non-regulated passing path
        return {
            "approval": "auto",
            "next": "audit_publish",
            "step_log": state["step_log"]
            + ["Supervisor: auto-approve non-regulated path", "Supervisor: route -> audit_publish"],
        }
    else:
        nxt = "END"

    return {
        "next": nxt,
        "step_log": state["step_log"] + [f"Supervisor: route -> {nxt}"],
    }
