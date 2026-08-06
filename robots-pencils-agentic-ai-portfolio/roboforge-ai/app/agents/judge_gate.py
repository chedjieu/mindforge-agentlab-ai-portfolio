"""Judge gate — architecture, groundedness, security, cost."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.state import ForgeState


class JudgeOut(BaseModel):
    architecture: float = Field(ge=0, le=1)
    groundedness: float = Field(ge=0, le=1)
    security_compliance: float = Field(ge=0, le=1)
    cost_realism: float = Field(ge=0, le=1)
    pass_: bool = Field(alias="pass", default=True)
    notes: str = ""

    model_config = {"populate_by_name": True}


def _heuristic(state: ForgeState) -> dict:
    bp = state.get("blueprint") or {}
    evidence = state.get("evidence") or []
    findings = state.get("security_findings") or {}
    blob = json.dumps(bp).lower()
    groundedness = 0.9 if evidence and bp.get("citations") else 0.55
    if "invented vpc" in blob:
        groundedness = 0.3
    security = 0.92 if findings.get("severity_max") != "critical" else 0.5
    if "skip encryption" in blob:
        security = 0.3
    architecture = 0.88 if bp.get("architecture") else 0.5
    cost = 0.85
    passed = (
        architecture >= 0.85
        and groundedness >= 0.85
        and security >= 0.9
        and cost >= 0.8
    )
    return {
        "architecture": architecture,
        "groundedness": groundedness,
        "security_compliance": security,
        "cost_realism": cost,
        "pass": passed,
        "notes": "heuristic",
    }


def judge_gate_node(state: ForgeState) -> dict:
    def _call() -> JudgeOut:
        return get_chat_model().with_structured_output(JudgeOut).invoke(
            [
                SystemMessage(
                    content=(
                        "Judge RoboForge outputs. Score architecture, groundedness, "
                        "security_compliance, cost_realism in 0..1. pass=true only if "
                        "architecture>=0.85, groundedness>=0.85, security_compliance>=0.9, "
                        "cost_realism>=0.8."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Blueprint: {json.dumps(state.get('blueprint'))[:2500]}\n"
                        f"Evidence: {json.dumps(state.get('evidence'))[:2000]}\n"
                        f"Security: {json.dumps(state.get('security_findings'))[:1000]}\n"
                        f"ROI: {json.dumps(state.get('roi'))[:800]}"
                    )
                ),
            ]
        )

    try:
        out = invoke_with_throttle_fallback(_call)
        scores = {
            "architecture": float(out.architecture),
            "groundedness": float(out.groundedness),
            "security_compliance": float(out.security_compliance),
            "cost_realism": float(out.cost_realism),
            "pass": bool(out.model_dump(by_alias=True).get("pass", True)),
            "notes": out.notes,
        }
        heur = _heuristic(state)
        # Prefer lower groundedness/security from heuristic when detecting bad phrases
        scores["groundedness"] = min(scores["groundedness"], heur["groundedness"])
        scores["security_compliance"] = min(
            scores["security_compliance"], heur["security_compliance"]
        )
        scores["pass"] = (
            scores["architecture"] >= 0.85
            and scores["groundedness"] >= 0.85
            and scores["security_compliance"] >= 0.9
            and scores["cost_realism"] >= 0.8
        )
    except Exception:
        scores = _heuristic(state)

    return {
        "judge_scores": scores,
        "step_log": state["step_log"]
        + [
            "judge_gate: "
            f"arch={scores['architecture']:.2f} ground={scores['groundedness']:.2f} "
            f"sec={scores['security_compliance']:.2f} cost={scores['cost_realism']:.2f} "
            f"pass={scores['pass']}"
        ],
    }
