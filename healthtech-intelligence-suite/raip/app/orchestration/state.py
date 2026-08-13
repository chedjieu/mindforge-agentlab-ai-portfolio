"""Typed LangGraph authoring state."""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from app.models.contracts import WorkflowStatus

Route = Literal[
    "evidence_retrieval",
    "evidence_synthesis",
    "drafting",
    "claim_verification",
    "quality_gates",
    "editorial",
    "publication_gate",
    "hitl",
    "persist",
    "END",
]


def _extend(a: list[Any] | None, b: list[Any] | None) -> list[Any]:
    return list(a or []) + list(b or [])


class AuthoringState(TypedDict, total=False):
    request_id: str
    thread_id: str
    project_id: str
    document_id: str
    section_id: str
    user_id: str
    tenant_id: str
    query: str
    template_id: str
    source_documents: list[str]
    retrieved_evidence: list[dict[str, Any]]
    evidence_map: dict[str, Any]
    claims: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    draft: str
    verified_draft: str
    editorial_done: bool
    gates: list[dict[str, Any]]
    scores: dict[str, Any]
    grounding_score: float
    citation_score: float
    regulatory_score: float
    safety_score: float
    template_score: float
    risk_level: str
    violations: list[str]
    review_required: bool
    review_decision: str
    workflow_status: str
    audit_events: Annotated[list[str], operator.add]
    model_version: str
    prompt_version: str
    retrieval_version: str
    evaluation_version: str
    tokens_in: int
    tokens_out: int
    estimated_cost_usd: float
    blocked: bool
    block_reason: str
    published: bool
    draft_id: str
    publication_checked: bool
    needs_final_persist: bool
    retrieval_done: bool
    synthesis_done: bool
    draft_done: bool
    claims_done: bool
    gates_done: bool
    step_count: int
    next: Route
    provenance: dict[str, Any]


def make_initial_state(
    *,
    request_id: str,
    thread_id: str,
    tenant_id: str,
    user_id: str,
    project_id: str,
    query: str,
    section_id: str = "Clinical Management Recommendations",
) -> AuthoringState:
    return {
        "request_id": request_id,
        "thread_id": thread_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "project_id": project_id,
        "query": query,
        "section_id": section_id,
        "source_documents": [],
        "retrieved_evidence": [],
        "evidence_map": {},
        "claims": [],
        "contradictions": [],
        "draft": "",
        "verified_draft": "",
        "editorial_done": False,
        "gates": [],
        "scores": {},
        "grounding_score": 0.0,
        "citation_score": 0.0,
        "regulatory_score": 0.0,
        "safety_score": 0.0,
        "template_score": 0.0,
        "risk_level": "medium",
        "violations": [],
        "review_required": True,
        "review_decision": "pending",
        "workflow_status": WorkflowStatus.RUNNING,
        "audit_events": [],
        "model_version": "fake",
        "prompt_version": "draft-v1",
        "retrieval_version": "hybrid-rrf-v1",
        "evaluation_version": "gates-v1",
        "tokens_in": 0,
        "tokens_out": 0,
        "estimated_cost_usd": 0.0,
        "blocked": False,
        "block_reason": "",
        "published": False,
        "draft_id": "",
        "publication_checked": False,
        "needs_final_persist": False,
        "retrieval_done": False,
        "synthesis_done": False,
        "draft_done": False,
        "claims_done": False,
        "gates_done": False,
        "step_count": 0,
        "next": "evidence_retrieval",
        "provenance": {},
    }
