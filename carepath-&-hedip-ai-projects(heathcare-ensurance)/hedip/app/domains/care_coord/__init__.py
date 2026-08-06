"""Care coordination thin domain."""

from __future__ import annotations

from app.rag.retrieval import hybrid_search
from app.state import HedipState
from app.tools.cases import load_case


def run_care_coord(state: HedipState) -> dict:
    case_id = state.get("case_id") or "CARE-001"
    case = load_case("care_coord", case_id)
    evidence = hybrid_search("discharge care coordination medication reconciliation", limit=3)
    tasks = case.get("tasks") or [
        "Reconcile discharge medications",
        "Schedule follow-up within 7 days",
        "Provide CHF education",
        "Arrange home health if eligible",
    ]
    escalate = bool(case.get("high_risk") or case.get("escalate"))
    draft = "# Care Coordination Plan\n\n" + "\n".join(f"- {t}" for t in tasks)
    if escalate:
        draft += "\n\n**Escalation:** high readmission risk — notify care manager."
    return {
        "case_payload": case,
        "domain_result": {"stages": ["discharge", "meds", "appointments", "education", "escalate"]},
        "evidence": evidence,
        "citations": [{"id": "C1", "source": e.get("source"), "text": (e.get("text") or "")[:200]} for e in evidence[:3]],
        "recommendation": {"decision": "care_plan", "tasks": tasks, "escalate": escalate},
        "draft": draft,
        "needs_hitl": escalate,
        "step_log": [f"CareCoord: {case_id} tasks={len(tasks)} escalate={escalate}"],
    }
