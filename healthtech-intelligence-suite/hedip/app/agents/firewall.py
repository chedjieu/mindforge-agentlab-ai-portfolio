from __future__ import annotations

from app.guardrails import check_escalate_patterns, check_query_guardrail
from app.state import HedipState


def firewall_node(state: HedipState) -> dict:
    text = " ".join([state.get("query") or "", str(state.get("case_id") or "")])
    refusal = check_query_guardrail(text)
    if refusal:
        return {
            "blocked": True,
            "block_reason": refusal,
            "final_response": refusal,
            "approval": "rejected",
            "published": False,
            "step_log": ["Firewall: BLOCKED"],
        }
    esc = check_escalate_patterns(text)
    log = ["Firewall: pass"]
    if esc:
        log.append(f"Firewall: escalate {esc}")
    return {"blocked": False, "needs_hitl": bool(esc) or state.get("needs_hitl", False), "step_log": log}
