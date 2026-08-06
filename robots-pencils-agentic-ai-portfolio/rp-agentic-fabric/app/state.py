"""Engagement state for the Agentic Delivery Fabric."""

from __future__ import annotations

from typing import Literal, TypedDict

Vertical = Literal["edtech", "healthcare", "finserv", "retail"]
Sensitivity = Literal["normal", "sensitive", "regulated"]
Approval = Literal["pending", "approved", "edited", "rejected", "auto"]
Route = Literal[
    "vertical_router",
    "compliance_mapper",
    "reuse_broker",
    "retrieval",
    "engagement_synthesizer",
    "judge_gate",
    "hitl",
    "audit_publish",
    "END",
]


class EngagementState(TypedDict):
    engagement_id: str
    tenant_id: str
    raw_brief: dict
    vertical: Vertical | None
    sensitivity: Sensitivity | None
    policy_pack_id: str | None
    guardrail_config: dict | None
    reuse_decided: bool
    reuse_decisions: list[dict]
    evidence: list[dict]
    draft_plan: dict | None
    judge_scores: dict | None
    approval: Approval
    published: bool
    audit_pack_id: str | None
    step_log: list[str]
    next: Route
