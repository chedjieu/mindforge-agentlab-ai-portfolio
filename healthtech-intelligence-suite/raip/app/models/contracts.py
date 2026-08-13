"""Pydantic domain contracts. Agents pass these shapes, not ad-hoc dicts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AuthorityTier(StrEnum):
    REGULATORY = "1_regulatory"
    GUIDELINE = "2_guideline"
    ORG_POLICY = "3_org_policy"
    APPROVED_REF = "4_approved_ref"
    HISTORICAL = "5_historical"
    UNVERIFIED = "6_unverified"


TIER_RANK: dict[str, int] = {
    AuthorityTier.REGULATORY: 1,
    AuthorityTier.GUIDELINE: 2,
    AuthorityTier.ORG_POLICY: 3,
    AuthorityTier.APPROVED_REF: 4,
    AuthorityTier.HISTORICAL: 5,
    AuthorityTier.UNVERIFIED: 6,
}


class SupportStatus(StrEnum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DraftStatus(StrEnum):
    DRAFT = "DRAFT"
    AI_VALIDATED = "AI_VALIDATED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEEDS_REVISION = "NEEDS_REVISION"
    PUBLICATION_BLOCKED = "PUBLICATION_BLOCKED"


class WorkflowStatus(StrEnum):
    RUNNING = "RUNNING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE"
    GROUNDING_FAILED = "GROUNDING_FAILED"
    SAFETY_FAILED = "SAFETY_FAILED"
    REGULATORY_FAILED = "REGULATORY_FAILED"
    SECURITY_FAILED = "SECURITY_FAILED"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
    PUBLICATION_BLOCKED = "PUBLICATION_BLOCKED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Role(StrEnum):
    AUTHOR = "AUTHOR"
    MEDICAL_REVIEWER = "MEDICAL_REVIEWER"
    REGULATORY_REVIEWER = "REGULATORY_REVIEWER"
    QUALITY_REVIEWER = "QUALITY_REVIEWER"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"


class EvidencePassage(BaseModel):
    chunk_id: str
    document_id: str
    version_id: str
    version_number: str = ""
    title: str = ""
    page_number: int = 1
    section: str = ""
    parent_section: str = ""
    text: str
    authority_tier: str = AuthorityTier.UNVERIFIED
    authority_score: float = 0.5
    effective_date: str | None = None
    superseded: bool = False
    retrieval_method: str = "hybrid"
    score: float = 0.0
    checksum: str = ""


class ClaimEvidenceLink(BaseModel):
    chunk_id: str
    document_id: str = ""
    version: str = ""
    page: int = 1
    section: str = ""
    support_type: str = "supports"
    support_score: float = 0.0
    citation: str = ""
    excerpt: str = ""


class ClaimRecord(BaseModel):
    claim_id: str
    claim: str
    claim_type: str = "factual"
    risk_level: str = "medium"
    support_status: SupportStatus = SupportStatus.UNSUPPORTED
    confidence: float = 0.0
    evidence: list[ClaimEvidenceLink] = Field(default_factory=list)


class Contradiction(BaseModel):
    topic: str
    statement_a: str
    statement_b: str
    source_a: str
    source_b: str
    resolution: str
    requires_hitl: bool = True


class GateResult(BaseModel):
    name: str
    passed: bool
    score: float = 0.0
    detail: str = ""
    critical: bool = False


class QualityScores(BaseModel):
    grounding: float = 0.0
    citation: float = 0.0
    coverage: float = 0.0
    regulatory: float = 0.0
    template: float = 0.0
    editorial: float = 0.0
    safety: float = 0.0
    overall: float = 0.0
    critical_safety_failure: bool = False
    publication_blocked: bool = True
    decision: str = "BLOCKED"


class ProvenanceRecord(BaseModel):
    request_id: str
    tenant_id: str
    model_version: str = "fake"
    prompt_version: str = "draft-v1"
    retrieval_version: str = "hybrid-rrf-v1"
    embedding_version: str = "fake-hash-64"
    evaluation_version: str = "gates-v1"
    policy_version: str = "authority-v1"
    agent_graph_version: str = "raip-graph-v1"
    source_versions: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class AuditPayload(BaseModel):
    action: str
    request_id: str
    tenant_id: str
    actor_id: str
    resource_type: str = ""
    resource_id: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
