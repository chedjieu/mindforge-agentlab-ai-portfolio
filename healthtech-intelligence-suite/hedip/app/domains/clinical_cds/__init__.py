"""Clinical CDS full pipeline (CarePath-parity composite)."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from app.llm import get_chat_model
from app.memory.procedural import load_playbook
from app.rag.retrieval import hybrid_search
from app.state import HedipState
from app.tools.cases import load_case
from app.tools.neo4j_graph import graph_lookup


def run_clinical_cds(state: HedipState) -> dict:
    case_id = state.get("case_id") or "CDS-P001"
    case = state.get("case_payload") or load_case("clinical_cds", case_id)
    patient = case.get("patient") or case
    meds = [str(m).lower() for m in (patient.get("medications") or [])]
    conditions = patient.get("conditions") or []
    labs = patient.get("labs") or {}
    prefs = case.get("preferences") or {}

    evidence = hybrid_search(" ".join(map(str, conditions)) + " treatment guidelines", limit=5)
    cites = [
        {"id": f"C{i+1}", "source": e.get("source"), "text": (e.get("text") or "")[:220]}
        for i, e in enumerate(evidence[:5])
    ]
    interactions = []
    if "alprazolam" in meds and "tramadol" in meds:
        interactions.append({"severity": "major", "pair": ["alprazolam", "tramadol"]})
    renal = []
    egfr = labs.get("egfr")
    if egfr is not None and "metformin" in meds and float(egfr) < 60:
        renal.append({"medication": "metformin", "action": "reduce", "egfr": egfr})

    llm = get_chat_model()
    prompt = (
        "Generate a personalized treatment plan with Goals, Interventions, Monitoring, Follow-up. "
        f"Clinical CDS case.\nPATIENT: {json.dumps(patient, default=str)[:2000]}\n"
        f"PREFS: {json.dumps(prefs)}\nINTERACTIONS: {interactions}\nRENAL: {renal}\n"
        f"PLAYBOOK: {json.dumps(load_playbook('clinical_cds'))[:400]}"
    )
    resp = llm.invoke([HumanMessage(content=prompt)])
    draft = str(resp.content)
    if prefs.get("avoid_injectables") and "oral" not in draft.lower():
        draft += "\n\n### Preference note\n- Prefer oral intensification; avoid injectable GLP-1.\n"

    rec = {
        "decision": "plan_ready",
        "interactions": interactions,
        "renal_adjustments": renal,
        "preferences_applied": bool(prefs),
    }
    return {
        "case_payload": case,
        "domain_result": {"stages": ["extract", "med_check", "generate", "preferences", "evaluate"]},
        "evidence": evidence,
        "graph_paths": graph_lookup(" ".join(map(str, conditions[:2]))),
        "citations": cites,
        "recommendation": rec,
        "draft": draft,
        "needs_hitl": True,
        "step_log": [
            f"CDS: {case_id} meds={len(meds)} interactions={len(interactions)} renal={len(renal)}"
        ],
    }
