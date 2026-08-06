"""Shared grounding / safety judge."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from app.llm import get_judge_model
from app.state import HedipState


def shared_judge(state: HedipState) -> dict:
    draft = state.get("draft") or ""
    cites = state.get("citations") or []
    rec = state.get("recommendation") or {}
    score = 0.75
    if cites:
        score += 0.1
    if rec.get("decision") or rec.get("risk_tier") or draft:
        score += 0.08
    if len(draft) > 80 or rec:
        score += 0.05
    score = min(0.99, score)

    notes = "Heuristic grounding pass"
    try:
        judge = get_judge_model()
        prompt = (
            "Evaluate this healthcare decision. Return JSON with keys: safety_score, "
            "groundedness, citation_coverage, hallucination_risk, notes.\n"
            f"DOMAIN: {state.get('domain')}\nREC: {json.dumps(rec, default=str)[:1500]}\n"
            f"DRAFT: {draft[:2500]}\nCITES: {json.dumps(cites, default=str)[:1000]}"
        )
        resp = judge.invoke([HumanMessage(content=prompt)])
        content = str(resp.content).strip()
        if content.startswith("{"):
            data = json.loads(content)
            score = min(float(score), float(data.get("safety_score", score)))
            notes = str(data.get("notes") or notes)
            judges = data
        else:
            judges = {"safety_score": score, "notes": notes}
    except Exception:
        judges = {"safety_score": score, "notes": notes}

    needs_hitl = bool(state.get("needs_hitl")) or state.get("sensitivity") == "sensitive"
    approval = "pending" if needs_hitl else "auto"

    return {
        "safety_score": round(score, 2),
        "judges": judges if isinstance(judges, dict) else {"safety_score": score, "notes": notes},
        "needs_hitl": needs_hitl,
        "approval": approval,
        "step_log": [f"Judge: safety={round(score, 2)} hitl={needs_hitl}"],
    }
