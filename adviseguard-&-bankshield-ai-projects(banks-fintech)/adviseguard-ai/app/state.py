"""AdviseGuard session state."""

from __future__ import annotations

from typing import Literal, TypedDict

Intent = Literal["advice", "fraud", "support", "mixed", "unknown"]
RiskBand = Literal["low", "medium", "high", "critical"]
Approval = Literal["pending", "approved", "edited", "rejected", "auto"]
Route = Literal[
    "intent_router",
    "hybrid_retriever",
    "graph_walker",
    "financial_advisor",
    "fraud_detector",
    "customer_support",
    "compliance_judge",
    "risk_judge",
    "synthesizer",
    "hitl",
    "response_publish",
    "END",
]


class SessionState(TypedDict):
    thread_id: str
    customer_id: str
    query: str
    intent: Intent | None
    needs_graph: bool
    needs_rag: bool
    run_advisor: bool
    run_fraud: bool
    run_support: bool
    goals: list[str]
    risk_tolerance: str
    txn_alert: dict
    customer_profile: dict
    retrieved_chunks: list[dict]
    graph_paths: list[dict]
    advice_draft: dict | None
    fraud_finding: dict | None
    support_answer: dict | None
    compliance_score: float | None
    risk_score: float | None
    risk_band: RiskBand | None
    final_response: dict | None
    grounding_score: float | None
    revise_count: int
    approval: Approval
    published: bool
    step_log: list[str]
    next: Route | None
