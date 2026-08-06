"""Human-in-the-loop approval (LangGraph interrupt)."""

from __future__ import annotations

from datetime import datetime, timezone

from langgraph.types import interrupt

from app.state import Approval, InvestigationState
from app.tools.publish import append_hitl_outcome


def hitl_node(state: InvestigationState) -> dict:
    queued_at = datetime.now(timezone.utc)
    payload = interrupt(
        {
            "recommendation": state.get("recommendation"),
            "risk_score": state.get("risk_score"),
            "risk_band": state.get("risk_band"),
            "fraud_types": state.get("fraud_types"),
            "grounding_score": state.get("grounding_score"),
            "evidence": state.get("evidence") or [],
            "graph_paths": state.get("graph_paths") or [],
            "reg_citations": [
                {"id": c.get("id"), "text": (c.get("text") or "")[:500]}
                for c in (state.get("reg_citations") or [])[:5]
            ],
            "similar_cases": [
                {"id": c.get("id"), "text": (c.get("text") or "")[:300]}
                for c in (state.get("similar_cases") or [])[:3]
            ],
            "alert": state.get("alert"),
            "case_id": state.get("case_id"),
            "query": state.get("query"),
            "queued_at": queued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    decided_at = datetime.now(timezone.utc)
    latency_s = max(0.0, (decided_at - queued_at).total_seconds())

    action = str((payload or {}).get("action", "approve")).lower()
    edited_body = (payload or {}).get("edited_body")
    rec_before = dict(state["recommendation"]) if state.get("recommendation") else {}
    rec = dict(rec_before)

    approval: Approval
    if action == "approve":
        approval = "approved"
        log = "HITL: approved"
    elif action == "edit":
        approval = "edited"
        if edited_body is not None:
            rec["summary"] = str(edited_body)
        log = "HITL: edited and approved"
    else:
        approval = "rejected"
        log = "HITL: rejected"

    try:
        append_hitl_outcome(
            {
                "thread_id": state.get("thread_id"),
                "case_id": state.get("case_id"),
                "action": action,
                "approval": approval,
                "risk_band": state.get("risk_band"),
                "grounding_score": state.get("grounding_score"),
                "recommendation_before": rec_before.get("summary"),
                "recommendation_after": rec.get("summary"),
                "queued_at": queued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "hitl_latency_seconds": round(latency_s, 3),
            }
        )
    except Exception:
        pass

    return {
        "approval": approval,
        "recommendation": rec,
        "step_log": state["step_log"] + [log],
    }
