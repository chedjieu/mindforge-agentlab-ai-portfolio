"""Enterprise knowledge agent state."""

from __future__ import annotations

from typing import Literal, TypedDict

Domain = Literal["engineering", "manufacturing", "hr", "support", "operations"]
Intent = Literal[
    "factoid",
    "procedure",
    "policy",
    "troubleshooting",
    "relationship",
    "unknown",
]
Sensitivity = Literal["normal", "sensitive"]
Approval = Literal["pending", "approved", "edited", "rejected", "auto"]
Route = Literal[
    "intent_router",
    "retriever",
    "graph_walker",
    "synthesizer",
    "grounder",
    "hitl",
    "answer_publish",
    "END",
]


class KnowledgeState(TypedDict):
    thread_id: str
    user_id: str
    role: str
    domain: Domain | None
    query: str
    intent: Intent | None
    needs_graph: bool
    sensitivity: Sensitivity
    retrieved_chunks: list[dict]
    graph_paths: list[dict]
    draft_answer: dict | None
    citations: list[dict]
    grounding_score: float | None
    revise_count: int
    approval: Approval
    published: bool
    step_log: list[str]
    next: Route | None
