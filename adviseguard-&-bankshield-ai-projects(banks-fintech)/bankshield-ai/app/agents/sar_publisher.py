"""SAR draft generation + case publish."""

from __future__ import annotations

from datetime import datetime, timezone

from app.guardrails import mask_pii
from app.state import InvestigationState
from app.tools.publish import publish_case


def sar_publisher_node(state: InvestigationState) -> dict:
    rec = state.get("recommendation") or {}
    alert = state.get("alert") or {}
    evidence = state.get("evidence") or []
    citations = state.get("reg_citations") or []

    narrative = mask_pii(
        f"Case {state.get('case_id')}: {rec.get('summary', '')}\n"
        f"Reasoning: {rec.get('reasoning', '')}\n"
        f"Fraud types: {state.get('fraud_types')}\n"
        f"Risk: {state.get('risk_band')} ({state.get('risk_score')})\n"
        f"Alert: {alert.get('description', '')}"
    )

    timeline = []
    for e in evidence:
        timeline.append(
            {
                "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "source": e.get("source"),
                "summary": mask_pii(str(e.get("summary") or "")),
            }
        )

    sar_draft = {
        "form": "SAR-demo",
        "case_id": state.get("case_id"),
        "filing_recommendation": rec.get("action"),
        "narrative": narrative,
        "evidence_timeline": timeline,
        "regulatory_references": rec.get("regulatory_refs")
        or [c.get("id") for c in citations if c.get("id") not in (None, "EMPTY")],
        "graph_explanation": rec.get("graph_explanation") or [],
        "similar_cases": rec.get("similar_case_ids") or [],
        "confidence": rec.get("confidence"),
        "grounding_score": state.get("grounding_score"),
        "investigator_approval": state.get("approval"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    publish_case(
        {
            "thread_id": state.get("thread_id"),
            "case_id": state.get("case_id"),
            "risk_band": state.get("risk_band"),
            "risk_score": state.get("risk_score"),
            "fraud_types": state.get("fraud_types"),
            "action": rec.get("action"),
            "approval": state.get("approval"),
            "sar_draft": sar_draft,
        }
    )

    return {
        "sar_draft": sar_draft,
        "published": True,
        "step_log": state["step_log"]
        + [f"SARPublisher: drafted action={rec.get('action')} published=True"],
    }
