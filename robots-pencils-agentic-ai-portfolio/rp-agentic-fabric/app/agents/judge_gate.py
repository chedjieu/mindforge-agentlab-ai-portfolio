"""Judge gate — compliance, faithfulness, cross-tenant leakage."""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.state import EngagementState

# Known demo foreign tenants — leakage if these appear in draft for another tenant
FOREIGN_TENANT_MARKERS = (
    "tenant-other",
    "tenant-rival",
    "acme-health-secret",
    "northbank-secret",
    "asu-secret-roster",
)


class JudgeOutput(BaseModel):
    compliance: float = Field(ge=0.0, le=1.0)
    faithfulness: float = Field(ge=0.0, le=1.0)
    leakage: float = Field(ge=0.0, le=1.0)
    pass_: bool = Field(alias="pass", default=True)
    notes: str = ""

    model_config = {"populate_by_name": True}


def _heuristic_scores(state: EngagementState) -> dict:
    draft = state.get("draft_plan") or {}
    blob = json.dumps(draft, ensure_ascii=False).lower()
    tenant = (state.get("tenant_id") or "").lower()

    leakage = 1.0
    for marker in FOREIGN_TENANT_MARKERS:
        if marker in blob and marker not in tenant:
            leakage = 0.0
            break
    # Flag other tenant_* ids like tenant-asu-demo — not English "tenant-scoped"
    if leakage >= 1.0:
        for m in re.findall(r"\btenant-[a-z0-9]+(?:-[a-z0-9]+)+\b", blob):
            if m in ("tenant-scoped",):
                continue
            if m != tenant:
                leakage = 0.0
                break

    evidence = state.get("evidence") or []
    faithfulness = 0.9 if evidence else 0.5
    if not draft.get("citations") and evidence:
        faithfulness = 0.7

    regs = (state.get("guardrail_config") or {}).get("regs") or []
    compliance = 0.93 if regs else 0.8
    forbidden = (state.get("guardrail_config") or {}).get("forbidden_topics") or []
    for topic in forbidden:
        if topic.replace("_", " ") in blob:
            compliance = 0.4

    passed = compliance >= 0.9 and faithfulness >= 0.85 and leakage >= 1.0
    return {
        "compliance": compliance,
        "faithfulness": faithfulness,
        "leakage": leakage,
        "pass": passed,
        "notes": "heuristic judge",
    }


def judge_gate_node(state: EngagementState) -> dict:
    draft = state.get("draft_plan") or {}
    evidence = state.get("evidence") or []

    def _call() -> JudgeOutput:
        model = get_chat_model()
        structured = model.with_structured_output(JudgeOutput)
        return structured.invoke(
            [
                SystemMessage(
                    content=(
                        "You are the judge gate for R&P Agentic Fabric. "
                        "Score compliance (policy pack), faithfulness (grounded in evidence), "
                        "and cross-tenant leakage (1.0 = no leak). "
                        "pass=true only if compliance>=0.9, faithfulness>=0.85, leakage>=1.0."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Tenant: {state['tenant_id']}\n"
                        f"Vertical: {state.get('vertical')}\n"
                        f"Policy: {json.dumps(state.get('guardrail_config') or {}, ensure_ascii=False)[:1500]}\n"
                        f"Draft: {json.dumps(draft, ensure_ascii=False)[:3000]}\n"
                        f"Evidence: {json.dumps(evidence, ensure_ascii=False)[:3000]}"
                    )
                ),
            ]
        )

    try:
        out = invoke_with_throttle_fallback(_call)
        scores = {
            "compliance": float(out.compliance),
            "faithfulness": float(out.faithfulness),
            "leakage": float(out.leakage),
            "pass": bool(
                getattr(out, "pass_", True)
                if hasattr(out, "pass_")
                else out.model_dump(by_alias=True).get("pass", True)
            ),
            "notes": out.notes,
        }
        # Leakage is authoritative from draft-only heuristic (avoids false positives
        # when evidence mentions the RiskFlag name "Cross-tenant leakage").
        heur = _heuristic_scores(state)
        scores["leakage"] = heur["leakage"]
        scores["pass"] = (
            scores["compliance"] >= 0.9
            and scores["faithfulness"] >= 0.85
            and scores["leakage"] >= 1.0
        )
        if heur["leakage"] < 1.0:
            scores["notes"] = (scores.get("notes") or "") + "; leakage flagged in draft"
    except Exception:
        scores = _heuristic_scores(state)

    return {
        "judge_scores": scores,
        "step_log": state["step_log"]
        + [
            "judge_gate: "
            f"compliance={scores['compliance']:.2f} "
            f"faithfulness={scores['faithfulness']:.2f} "
            f"leakage={scores['leakage']:.2f} pass={scores['pass']}"
        ],
    }
