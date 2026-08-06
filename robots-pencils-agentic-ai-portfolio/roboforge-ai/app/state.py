"""Forge engagement state."""

from __future__ import annotations

from typing import Literal, TypedDict

Domain = Literal["modernize", "agentic", "rag", "migration"]
Approval = Literal["pending", "approved", "edited", "rejected"]
Route = Literal[
    "intake_analyzer",
    "estate_assessor",
    "knowledge_builder",
    "security_compliance",
    "solution_architect",
    "roi_optimizer",
    "judge_gate",
    "hitl",
    "delivery_publish",
    "END",
]


class ForgeState(TypedDict):
    engagement_id: str
    client_id: str
    raw_pack: dict
    domain: Domain | None
    intake: dict | None
    estate: dict | None
    evidence: list[dict]
    security_findings: dict | None
    blueprint: dict | None
    roi: dict | None
    judge_scores: dict | None
    approval: Approval
    published: bool
    delivery_pack_id: str | None
    step_log: list[str]
    next: Route
