from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

Domain = Literal[
    "prior_auth",
    "claims",
    "clinical_cds",
    "care_coord",
    "knowledge",
    "fraud",
    "pop_health",
    "rcm",
]

Approval = Literal["pending", "approved", "edited", "rejected", "auto"]


def _extend(a: list[Any] | None, b: list[Any] | None) -> list[Any]:
    return list(a or []) + list(b or [])


class HedipState(TypedDict, total=False):
    thread_id: str
    user_id: str
    role: str
    domain: Domain | None
    query: str
    case_id: str
    abac: dict[str, Any]
    sensitivity: str
    intent: dict[str, Any]
    case_payload: dict[str, Any]
    domain_result: dict[str, Any]
    evidence: Annotated[list[dict[str, Any]], _extend]
    graph_paths: list[dict[str, Any]]
    draft: str
    recommendation: dict[str, Any]
    citations: list[dict[str, Any]]
    judges: dict[str, Any]
    compliance: dict[str, Any]
    safety_score: float | None
    needs_hitl: bool
    approval: Approval
    published: bool
    final_response: str
    step_log: Annotated[list[str], operator.add]
    blocked: bool
    block_reason: str
    next: str
