"""Supervisor — pure-logic routing for RoboForge."""

from __future__ import annotations

from app.state import ForgeState, Route


def supervisor_node(state: ForgeState) -> dict:
    nxt: Route = "END"
    if state["approval"] == "rejected":
        nxt = "END"
    elif state["intake"] is None:
        nxt = "intake_analyzer"
    elif state["estate"] is None:
        nxt = "estate_assessor"
    elif state["evidence"] == []:
        nxt = "knowledge_builder"
    elif state["security_findings"] is None:
        nxt = "security_compliance"
    elif state["blueprint"] is None:
        nxt = "solution_architect"
    elif state["roi"] is None:
        nxt = "roi_optimizer"
    elif state["judge_scores"] is None:
        nxt = "judge_gate"
    elif state["approval"] == "pending":
        nxt = "hitl"
    elif state["approval"] in ("approved", "edited") and not state["published"]:
        nxt = "delivery_publish"
    else:
        nxt = "END"
    return {"next": nxt, "step_log": state["step_log"] + [f"Supervisor: route -> {nxt}"]}
