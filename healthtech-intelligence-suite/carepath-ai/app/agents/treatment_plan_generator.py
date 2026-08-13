"""Treatment plan generation agent."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from app.llm import get_chat_model
from app.memory.episodic import load_episodic
from app.memory.procedural import load_protocols_for_conditions
from app.memory.semantic import load_semantic_feedback
from app.rag.retrieval import hybrid_search
from app.state import TreatmentPlanState


def treatment_plan_generator(state: TreatmentPlanState) -> dict:
    profile = state.get("patient_profile") or {}
    review = state.get("medication_review") or {}
    patient_id = state.get("patient_id") or profile.get("patient_id") or "P001"
    feedback = state.get("judge_feedback") or ""
    revise = int(state.get("revise_count") or 0)

    protocols = load_protocols_for_conditions(profile.get("conditions") or [])
    episodic = load_episodic(str(patient_id))
    semantic = load_semantic_feedback(str(patient_id))

    query_bits = " ".join(profile.get("conditions") or []) + " chronic care treatment plan"
    evidence = list(state.get("retrieved_evidence") or [])
    if not evidence:
        evidence = hybrid_search(query_bits, limit=6)

    citations = []
    for i, chunk in enumerate(evidence[:6]):
        citations.append(
            {
                "id": f"C{i+1}",
                "source": chunk.get("source") or chunk.get("id") or f"chunk-{i}",
                "text": (chunk.get("text") or "")[:240],
                "domain": chunk.get("domain"),
            }
        )
    for i, proto in enumerate(protocols[:3]):
        citations.append(
            {
                "id": f"P{i+1}",
                "source": proto.get("id") or proto.get("name") or f"protocol-{i}",
                "text": (proto.get("summary") or proto.get("title") or "")[:240],
                "domain": "protocol",
            }
        )

    context = {
        "profile": profile,
        "medication_review": {
            "summary": review.get("summary"),
            "interactions": review.get("interactions"),
            "renal_adjustments": review.get("renal_adjustments"),
        },
        "protocols": protocols,
        "episodic": episodic[-3:],
        "semantic_feedback": semantic[-3:],
        "citations": citations,
        "judge_feedback": feedback,
        "preferences": state.get("patient_preferences") or {},
    }

    llm = get_chat_model()
    prompt = (
        "Generate a personalized treatment plan with sections: Goals, Interventions, "
        "Monitoring, Follow-up. Address medication interactions and renal adjustments. "
        "Cite evidence ids where relevant.\n\n"
        f"CONTEXT:\n{json.dumps(context, default=str)[:6000]}\n"
    )
    if feedback:
        prompt += f"\nRevise based on judge feedback: {feedback}\n"

    resp = llm.invoke([HumanMessage(content=prompt)])
    draft = str(resp.content)

    updates: dict = {
        "draft_plan": draft,
        "citations": citations,
        "retrieved_evidence": evidence,
        "needs_revise": False,
        "safety_score": None,  # force re-eval after regenerate
        "preferences_applied": False if state.get("patient_preferences") else True,
        "step_log": [
            f"Generator: drafted plan ({len(draft)} chars) with {len(citations)} citations"
            + (f"; revise#{revise}" if feedback else "")
        ],
    }
    if feedback:
        updates["revise_count"] = revise + 1
        updates["judge_feedback"] = None
    return updates
