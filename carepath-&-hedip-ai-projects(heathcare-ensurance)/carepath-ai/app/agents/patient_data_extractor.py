"""Patient data extraction agent — EHR / notes → structured profile + RAG/KG enrich."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage

from app.llm import get_chat_model
from app.memory.episodic import load_episodic
from app.rag.retrieval import hybrid_search
from app.state import TreatmentPlanState
from app.tools.neo4j_graph import guideline_for_condition, graph_lookup

ROOT = Path(__file__).resolve().parents[2]
PATIENTS = ROOT / "data" / "patients"


def _load_patient_files(patient_id: str) -> dict[str, Any]:
    folder = PATIENTS / patient_id
    payload: dict[str, Any] = {"patient_id": patient_id}
    ehr = folder / "ehr_bundle.json"
    notes = folder / "notes.md"
    prefs = folder / "preferences.json"
    if ehr.exists():
        payload["ehr"] = json.loads(ehr.read_text(encoding="utf-8"))
    if notes.exists():
        payload["notes"] = notes.read_text(encoding="utf-8")
    if prefs.exists():
        payload["preferences_file"] = json.loads(prefs.read_text(encoding="utf-8"))
    return payload


def _profile_from_ehr(raw: dict[str, Any]) -> dict[str, Any]:
    ehr = raw.get("ehr") or raw.get("raw_ehr_payload") or {}
    conditions = ehr.get("conditions") or []
    medications = ehr.get("medications") or []
    allergies = ehr.get("allergies") or []
    labs = ehr.get("labs") or {}
    lifestyle = ehr.get("lifestyle") or {}
    # normalize med names
    med_names = []
    for m in medications:
        if isinstance(m, dict):
            med_names.append(str(m.get("name") or m.get("medication") or "").lower())
        else:
            med_names.append(str(m).lower())
    cond_names = []
    for c in conditions:
        if isinstance(c, dict):
            cond_names.append(str(c.get("name") or c.get("display") or ""))
        else:
            cond_names.append(str(c))
    return {
        "patient_id": raw.get("patient_id"),
        "conditions": cond_names,
        "medications": [m for m in med_names if m],
        "allergies": allergies,
        "labs": labs,
        "lifestyle": lifestyle,
        "notes_excerpt": (raw.get("notes") or "")[:800],
    }


def patient_data_extractor(state: TreatmentPlanState) -> dict:
    patient_id = state.get("patient_id") or "P001"
    raw = state.get("raw_ehr_payload") or _load_patient_files(patient_id)
    if "patient_id" not in raw:
        raw["patient_id"] = patient_id

    profile = _profile_from_ehr(raw)

    # Optional LLM enrichment only for missing fields (do not clobber structured EHR)
    try:
        llm = get_chat_model()
        prompt = (
            "Extract a clinical profile as JSON from this EHR payload.\n"
            f"{json.dumps(raw)[:4000]}"
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        content = str(resp.content)
        if content.strip().startswith("{"):
            enriched = json.loads(content)
            for key in ("conditions", "medications", "allergies", "labs", "lifestyle"):
                if not profile.get(key) and enriched.get(key):
                    profile[key] = enriched[key]
    except Exception:
        pass

    evidence = hybrid_search(
        " ".join(profile.get("conditions") or []) + " treatment guidelines",
        limit=5,
    )
    graph_paths: list[dict[str, Any]] = []
    for cond in (profile.get("conditions") or [])[:3]:
        graph_paths.extend(guideline_for_condition(cond, limit=3))
        graph_paths.extend(graph_lookup("Condition", cond, limit=2))

    episodic = load_episodic(patient_id)
    profile["episodic_count"] = len(episodic)

    prefs = state.get("patient_preferences") or raw.get("preferences_file") or {}

    return {
        "raw_ehr_payload": raw if isinstance(raw, dict) else {"raw": raw},
        "patient_profile": profile,
        "patient_preferences": prefs,
        "retrieved_evidence": evidence,
        "graph_paths": graph_paths,
        "step_log": [
            f"Extractor: profile for {patient_id} — "
            f"{len(profile.get('conditions') or [])} conditions, "
            f"{len(profile.get('medications') or [])} meds, "
            f"{len(evidence)} evidence chunks"
        ],
    }
