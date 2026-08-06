"""Population health thin domain."""

from __future__ import annotations

from app.rag.retrieval import hybrid_search
from app.state import HedipState
from app.tools.cases import load_case


def run_pop_health(state: HedipState) -> dict:
    case_id = state.get("case_id") or "POP-001"
    case = load_case("pop_health", case_id)
    risk = float(case.get("risk_score") or 0.35)
    tier = "high" if risk >= 0.7 else "moderate" if risk >= 0.4 else "low"
    actions = case.get("actions") or [
        "Outreach for care gap closure",
        "Review med adherence",
        "Schedule PCP visit",
    ]
    evidence = hybrid_search("population health readmission risk diabetes heart failure", limit=3)
    draft = f"# Population Health Risk\n\n**Tier:** {tier} ({risk})\n\n" + "\n".join(f"- {a}" for a in actions)
    return {
        "case_payload": case,
        "domain_result": {"stages": ["risk", "vitals", "labs", "sdoh", "recommend"]},
        "evidence": evidence,
        "citations": [{"id": "C1", "source": e.get("source"), "text": (e.get("text") or "")[:200]} for e in evidence[:3]],
        "recommendation": {"decision": "risk_stratified", "risk_tier": tier, "risk_score": risk, "actions": actions},
        "draft": draft,
        "needs_hitl": False,
        "step_log": [f"PopHealth: {case_id} tier={tier}"],
    }
