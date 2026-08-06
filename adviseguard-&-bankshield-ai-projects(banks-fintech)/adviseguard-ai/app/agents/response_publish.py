"""Publish approved response."""

from __future__ import annotations

from app.guardrails import mask_pii
from app.state import SessionState
from app.tools.publish import publish_response


def response_publish_node(state: SessionState) -> dict:
    resp = dict(state.get("final_response") or {})
    if resp.get("summary"):
        resp["summary"] = mask_pii(str(resp["summary"]))
    publish_response(
        {
            "thread_id": state.get("thread_id"),
            "customer_id": state.get("customer_id"),
            "intent": state.get("intent"),
            "approval": state.get("approval"),
            "risk_band": state.get("risk_band"),
            "response": resp,
        }
    )
    return {
        "final_response": resp,
        "published": True,
        "step_log": state["step_log"] + ["Publish: response logged"],
    }
