"""Human-in-the-loop approval node (LangGraph interrupt)."""

from __future__ import annotations

from datetime import datetime, timezone

from langgraph.types import interrupt

from app.hitl_log import append_hitl_outcome
from app.state import Approval, KnowledgeState


def hitl_node(state: KnowledgeState) -> dict:
    """Pause for human approval; resume with action approve/edit/reject."""
    queued_at = datetime.now(timezone.utc)
    payload = interrupt(
        {
            "draft": state.get("draft_answer"),
            "citations": state.get("citations") or [],
            "grounding_score": state.get("grounding_score"),
            "domain": state.get("domain"),
            "query": state.get("query"),
            "retrieved_chunks": state.get("retrieved_chunks") or [],
            "graph_paths": state.get("graph_paths") or [],
            "queued_at": queued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    decided_at = datetime.now(timezone.utc)
    latency_s = max(0.0, (decided_at - queued_at).total_seconds())

    action = str((payload or {}).get("action", "approve")).lower()
    edited_body = (payload or {}).get("edited_body")
    draft_before = dict(state["draft_answer"]) if state.get("draft_answer") else {}
    draft = dict(draft_before)

    approval: Approval
    if action == "approve":
        approval = "approved"
        log = "HITL: approved"
    elif action == "edit":
        approval = "edited"
        if edited_body is not None:
            draft["answer"] = str(edited_body)
        log = "HITL: edited and approved"
    else:
        approval = "rejected"
        log = "HITL: rejected"

    try:
        append_hitl_outcome(
            {
                "thread_id": state.get("thread_id"),
                "domain": state.get("domain"),
                "action": action,
                "approval": approval,
                "query": state.get("query"),
                "grounding_score": state.get("grounding_score"),
                "draft_before": draft_before.get("answer"),
                "draft_after": draft.get("answer"),
                "recommended_action": draft_before.get("recommended_action"),
                "queued_at": queued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "hitl_latency_seconds": round(latency_s, 3),
            }
        )
    except Exception:
        pass

    return {
        "approval": approval,
        "draft_answer": draft,
        "step_log": state["step_log"] + [log],
    }
