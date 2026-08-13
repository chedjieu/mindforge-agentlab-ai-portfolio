"""Revenue cycle coding thin domain."""

from __future__ import annotations

from app.rag.retrieval import hybrid_search
from app.state import HedipState
from app.tools.cases import load_case


def run_rcm(state: HedipState) -> dict:
    case_id = state.get("case_id") or "RCM-001"
    case = load_case("rcm", case_id)
    icd = case.get("suggested_icd10") or ["E11.9"]
    cpt = case.get("suggested_cpt") or ["99213"]
    gaps = case.get("documentation_gaps") or []
    evidence = hybrid_search("medical coding documentation ICD CPT compliance", limit=3)
    draft = (
        f"# RCM Coding Assist\n\n**ICD-10:** {icd}\n**CPT:** {cpt}\n"
        f"**Documentation gaps:** {gaps or ['none']}\n"
    )
    return {
        "case_payload": case,
        "domain_result": {"stages": ["note", "icd", "cpt", "compliance"]},
        "evidence": evidence,
        "citations": [{"id": "C1", "source": e.get("source"), "text": (e.get("text") or "")[:200]} for e in evidence[:3]],
        "recommendation": {
            "decision": "coding_draft",
            "icd10": icd,
            "cpt": cpt,
            "documentation_gaps": gaps,
        },
        "draft": draft,
        "needs_hitl": bool(gaps),
        "step_log": [f"RCM: {case_id} icd={icd} cpt={cpt}"],
    }
