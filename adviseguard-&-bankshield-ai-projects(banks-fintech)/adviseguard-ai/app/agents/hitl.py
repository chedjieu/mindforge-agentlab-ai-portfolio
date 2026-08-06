"""Human-in-the-loop approval (LangGraph interrupt)."""

from __future__ import annotations

from datetime import datetime, timezone

from langgraph.types import interrupt

from app.state import Approval, SessionState
from app.tools.publish import append_hitl_outcome


def hitl_node(state: SessionState) -> dict:
    queued_at = datetime.now(timezone.utc)
    payload = interrupt(
        {
            "final_response": state.get("final_response"),
            "advice_draft": state.get("advice_draft"),
            "fraud_finding": state.get("fraud_finding"),
            "risk_band": state.get("risk_band"),
            "risk_score": state.get("risk_score"),
            "compliance_score": state.get("compliance_score"),
            "grounding_score": state.get("grounding_score"),
            "customer_id": state.get("customer_id"),
            "query": state.get("query"),
            "intent": state.get("intent"),
            "queued_at": queued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    action = str((payload or {}).get("action", "approve")).lower()
    edited_body = (payload or {}).get("edited_body")
    resp = dict(state["final_response"]) if state.get("final_response") else {}

    if action == "approve":
        approval: Approval = "approved"
        log = "HITL: approved"
    elif action == "edit":
        approval = "edited"
        if edited_body is not None:
            resp["summary"] = str(edited_body)
        log = "HITL: edited and approved"
    else:
        approval = "rejected"
        log = "HITL: rejected"

    try:
        append_hitl_outcome(
            {
                "thread_id": state.get("thread_id"),
                "customer_id": state.get("customer_id"),
                "action": action,
                "approval": approval,
                "intent": state.get("intent"),
                "risk_band": state.get("risk_band"),
                "queued_at": queued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        )
    except Exception:
        pass

    return {
        "approval": approval,
        "final_response": resp,
        "step_log": state["step_log"] + [log],
    }
