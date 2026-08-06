"""Supervisor — routes knowledge queries to the next worker (pure logic, no LLM)."""

from __future__ import annotations

from app.state import KnowledgeState, Route


def supervisor_node(state: KnowledgeState) -> dict:
    """Decide the next node based on current knowledge-query progress."""
    nxt: Route = "END"

    if state["approval"] == "rejected":
        nxt = "END"
    elif state["intent"] is None:
        nxt = "intent_router"
    elif state["retrieved_chunks"] == []:
        nxt = "retriever"
    elif state["needs_graph"] and state["graph_paths"] == []:
        nxt = "graph_walker"
    elif state["draft_answer"] is None:
        nxt = "synthesizer"
    elif state["grounding_score"] is None:
        nxt = "grounder"
    elif state["approval"] == "pending":
        nxt = "hitl"
    elif state["approval"] in ("approved", "edited", "auto") and not state["published"]:
        nxt = "answer_publish"
    else:
        nxt = "END"

    return {
        "next": nxt,
        "step_log": state["step_log"] + [f"Supervisor: route -> {nxt}"],
    }
