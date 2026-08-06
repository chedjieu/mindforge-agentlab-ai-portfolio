"""BankShield investigation agent state."""

from __future__ import annotations

from typing import Literal, TypedDict

FraudType = Literal[
    "wire",
    "ach",
    "card",
    "ato",
    "mule",
    "sanctions",
    "aml",
    "app_bec",
    "instant_pay",
    "unknown",
]
PaymentRail = Literal["wire", "ach", "card", "rtp", "fednow", "internal", "unknown"]
RiskBand = Literal["low", "medium", "high", "critical"]
Sensitivity = Literal["normal", "sensitive"]
Approval = Literal["pending", "approved", "edited", "rejected", "auto"]
Route = Literal[
    "triage_router",
    "identity_kyc",
    "transaction_intel",
    "graph_walker",
    "regulatory_rag",
    "similar_case_retriever",
    "risk_scorer",
    "recommender",
    "grounder_judge",
    "hitl",
    "sar_publisher",
    "END",
]


class InvestigationState(TypedDict):
    thread_id: str
    case_id: str
    investigator_id: str
    alert: dict
    query: str
    fraud_types: list[str] | None
    payment_rail: PaymentRail | None
    needs_graph: bool
    needs_identity: bool
    sensitivity: Sensitivity
    entities: dict
    identity_findings: list[dict]
    txn_features: dict | None
    evidence: list[dict]
    graph_paths: list[dict]
    reg_citations: list[dict]
    similar_cases: list[dict]
    risk_score: float | None
    risk_band: RiskBand | None
    recommendation: dict | None
    grounding_score: float | None
    revise_count: int
    approval: Approval
    sar_draft: dict | None
    published: bool
    step_log: list[str]
    next: Route | None
