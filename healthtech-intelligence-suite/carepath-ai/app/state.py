from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


def _extend_list(a: list[Any] | None, b: list[Any] | None) -> list[Any]:
    return list(a or []) + list(b or [])


Approval = Literal["pending", "approved", "edited", "rejected", "auto"]

Route = Literal[
    "patient_data_extractor",
    "medication_interaction_checker",
    "treatment_plan_generator",
    "patient_preference_agent",
    "treatment_plan_evaluator",
    "hitl",
    "plan_publish",
    "END",
]


class TreatmentPlanState(TypedDict, total=False):
    thread_id: str
    clinician_id: str
    patient_id: str
    query: str
    patient_preferences: dict[str, Any]
    raw_ehr_payload: dict[str, Any]
    patient_profile: dict[str, Any] | None
    retrieved_evidence: Annotated[list[dict[str, Any]], _extend_list]
    graph_paths: list[dict[str, Any]]
    medication_review: dict[str, Any] | None
    draft_plan: str | None
    citations: list[dict[str, Any]]
    preferences_applied: bool
    safety_score: float | None
    judge_feedback: str | None
    needs_revise: bool
    revise_count: int
    approval: Approval
    published: bool
    final_plan: str
    step_log: Annotated[list[str], operator.add]
    blocked: bool
    block_reason: str
    next: Route
