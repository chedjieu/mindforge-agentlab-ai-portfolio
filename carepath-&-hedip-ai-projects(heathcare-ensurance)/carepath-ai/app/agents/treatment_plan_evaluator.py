"""Treatment plan evaluator (judge) — safety, guidelines, citations."""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage

from app.llm import get_judge_model
from app.memory.procedural import load_protocols_for_conditions
from app.state import TreatmentPlanState

REQUIRED_SECTIONS = ("goal", "intervention", "monitor", "follow")


def _heuristic_score(state: TreatmentPlanState) -> dict:
    draft = (state.get("draft_plan") or "").lower()
    citations = state.get("citations") or []
    review = state.get("medication_review") or {}
    profile = state.get("patient_profile") or {}
    allergies = [str(a).lower() for a in (profile.get("allergies") or [])]

    section_hits = sum(1 for s in REQUIRED_SECTIONS if s in draft)
    completeness = section_hits / len(REQUIRED_SECTIONS)

    citation_coverage = 1.0 if citations else 0.4
    if citations and ("[c" in draft or "c1" in draft or "protocol" in draft or "guideline" in draft):
        citation_coverage = 0.95

    allergy_hit = any(a and a in draft for a in allergies if a not in ("sulfa",))
    # sulfa allergy should not appear as a prescribed sulfa drug
    sulfa_risk = "sulfa" in allergies and bool(re.search(r"\b(bactrim|sulfamethoxazole)\b", draft))

    major = int(review.get("major_count") or 0)
    addresses_meds = any(
        token in draft
        for token in ("interaction", "metformin", "egfr", "renal", "ckd", "dose")
    )
    safety = 0.7
    if completeness >= 0.75:
        safety += 0.1
    if citation_coverage >= 0.8:
        safety += 0.08
    if addresses_meds or major == 0:
        safety += 0.07
    if sulfa_risk or allergy_hit:
        safety -= 0.25
    safety = max(0.0, min(0.99, safety))

    needs_revise = safety < 0.90 or completeness < 0.75
    feedback = []
    if completeness < 0.75:
        feedback.append("Add missing Goals/Interventions/Monitoring/Follow-up sections.")
    if not addresses_meds and major:
        feedback.append("Explicitly address major medication interactions and renal dosing.")
    if sulfa_risk:
        feedback.append("Remove sulfa-containing agents given documented allergy.")
    if not feedback:
        feedback.append("Plan meets heuristic safety bar.")

    return {
        "safety_score": round(safety, 2),
        "guideline_adherence": round(0.85 + 0.05 * completeness, 2),
        "citation_coverage": round(citation_coverage, 2),
        "completeness": round(completeness, 2),
        "needs_revise": needs_revise,
        "feedback": " ".join(feedback),
    }


def treatment_plan_evaluator(state: TreatmentPlanState) -> dict:
    profile = state.get("patient_profile") or {}
    protocols = load_protocols_for_conditions(profile.get("conditions") or [])
    heur = _heuristic_score(state)

    try:
        judge = get_judge_model()
        prompt = (
            "Evaluate this treatment plan. Return JSON with keys: safety_score, "
            "guideline_adherence, citation_coverage, completeness, needs_revise, feedback.\n"
            f"PROFILE: {json.dumps(profile, default=str)[:1500]}\n"
            f"MED_REVIEW: {json.dumps(state.get('medication_review') or {}, default=str)[:1500]}\n"
            f"PROTOCOLS: {json.dumps(protocols, default=str)[:1000]}\n"
            f"CITATIONS: {json.dumps(state.get('citations') or [], default=str)[:1000]}\n"
            f"PLAN:\n{(state.get('draft_plan') or '')[:4000]}\n"
        )
        resp = judge.invoke([HumanMessage(content=prompt)])
        content = str(resp.content).strip()
        if content.startswith("{"):
            llm_score = json.loads(content)
            # Blend: take min safety to be conservative
            heur["safety_score"] = round(
                min(float(heur["safety_score"]), float(llm_score.get("safety_score", heur["safety_score"]))),
                2,
            )
            heur["feedback"] = str(llm_score.get("feedback") or heur["feedback"])
            for k in ("guideline_adherence", "citation_coverage", "completeness"):
                if k in llm_score:
                    heur[k] = float(llm_score[k])
            # Conservative: revise if either heuristic or judge says so when below bar
            llm_revise = bool(llm_score.get("needs_revise"))
            heur["needs_revise"] = (heur["needs_revise"] or llm_revise) and heur["safety_score"] < 0.90
    except Exception:
        pass

    # Ship bar: safety >= 0.90; allow at most 2 revise loops
    revise_count = int(state.get("revise_count") or 0)
    below_bar = float(heur["safety_score"]) < 0.90
    needs_revise = below_bar and revise_count < 2

    updates: dict = {
        "safety_score": float(heur["safety_score"]),
        "judge_feedback": heur["feedback"],
        "needs_revise": needs_revise,
        "step_log": [
            f"Evaluator: safety={heur['safety_score']} "
            f"citations={heur['citation_coverage']} revise={needs_revise}"
        ],
    }

    if needs_revise:
        updates["draft_plan"] = None  # supervisor will re-route to generator
        updates["safety_score"] = None
    else:
        updates["approval"] = "pending"  # always HITL in v1
        updates["needs_revise"] = False

    return updates
