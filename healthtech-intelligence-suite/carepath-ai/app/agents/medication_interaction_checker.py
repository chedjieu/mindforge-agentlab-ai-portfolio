"""Medication interaction checker — KG + seed drug DB."""

from __future__ import annotations

from typing import Any

from app.state import TreatmentPlanState
from app.tools.drug_db_mock import check_interactions, check_renal_adjustments
from app.tools.neo4j_graph import find_interactions


def medication_interaction_checker(state: TreatmentPlanState) -> dict:
    profile = state.get("patient_profile") or {}
    meds = [str(m).lower() for m in (profile.get("medications") or [])]
    labs = profile.get("labs") or {}
    allergies = [str(a).lower() for a in (profile.get("allergies") or [])]

    seed_hits = check_interactions(meds)
    kg_hits = find_interactions(meds, limit=10)
    renal = check_renal_adjustments(meds, labs)

    allergy_flags: list[dict[str, Any]] = []
    for med in meds:
        for allergy in allergies:
            if allergy and allergy in med:
                allergy_flags.append(
                    {
                        "severity": "major",
                        "pair": [med, allergy],
                        "note": f"Possible allergy conflict: {med} vs {allergy}",
                    }
                )

    # merge unique
    interactions = list(seed_hits) + list(allergy_flags)
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for item in interactions:
        key = json_key(item)
        if key not in seen:
            seen.add(key)
            merged.append(item)

    major = [i for i in merged if str(i.get("severity", "")).lower() == "major"]
    moderate = [i for i in merged if str(i.get("severity", "")).lower() == "moderate"]

    review = {
        "medications": meds,
        "interactions": merged,
        "kg_paths": kg_hits,
        "renal_adjustments": renal,
        "major_count": len(major),
        "moderate_count": len(moderate),
        "summary": (
            f"{len(major)} major, {len(moderate)} moderate interactions; "
            f"{len(renal)} renal dosing notes"
        ),
    }

    return {
        "medication_review": review,
        "graph_paths": list(state.get("graph_paths") or []) + list(kg_hits),
        "step_log": [f"MedChecker: {review['summary']}"],
    }


def json_key(item: dict[str, Any]) -> str:
    pair = item.get("pair") or []
    return f"{item.get('severity')}|{'|'.join(sorted(str(p) for p in pair))}|{item.get('note', '')[:40]}"
