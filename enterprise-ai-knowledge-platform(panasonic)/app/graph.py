"""EGKP LangGraph — supervisor routes workers in a loop."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore

from app.agents.answer_publish import answer_publish_node
from app.agents.graph_walker import graph_walker_node
from app.agents.grounder import grounder_node
from app.agents.hitl import hitl_node
from app.agents.intent_router import intent_router_node
from app.agents.retriever import retriever_node
from app.agents.supervisor import supervisor_node
from app.agents.synthesizer import synthesizer_node
from app.state import KnowledgeState

CHECKPOINT_PATH = Path(__file__).resolve().parent.parent / "checkpoints.sqlite"

WORKERS = (
    "intent_router",
    "retriever",
    "graph_walker",
    "synthesizer",
    "grounder",
    "hitl",
    "answer_publish",
)


def build_graph_with_backends(saver: Any, store: BaseStore | None = None):
    """Compile the knowledge graph with injected checkpoint saver and store."""
    builder = StateGraph(KnowledgeState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("intent_router", intent_router_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("graph_walker", graph_walker_node)
    builder.add_node("synthesizer", synthesizer_node)
    builder.add_node("grounder", grounder_node)
    builder.add_node("hitl", hitl_node)
    builder.add_node("answer_publish", answer_publish_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {
            "intent_router": "intent_router",
            "retriever": "retriever",
            "graph_walker": "graph_walker",
            "synthesizer": "synthesizer",
            "grounder": "grounder",
            "hitl": "hitl",
            "answer_publish": "answer_publish",
            "END": END,
        },
    )
    for worker in WORKERS:
        builder.add_edge(worker, "supervisor")

    return builder.compile(checkpointer=saver, store=store)


def build_graph():
    """Compile with a SqliteSaver checkpointer (local dev)."""
    conn = sqlite3.connect(str(CHECKPOINT_PATH), check_same_thread=False)
    return build_graph_with_backends(SqliteSaver(conn))


def make_initial_state(
    *,
    thread_id: str,
    query: str,
    user_id: str = "demo-user",
    role: str = "engineer",
) -> KnowledgeState:
    return {
        "thread_id": thread_id,
        "user_id": user_id,
        "role": role,
        "domain": None,
        "query": query,
        "intent": None,
        "needs_graph": False,
        "sensitivity": "normal",
        "retrieved_chunks": [],
        "graph_paths": [],
        "draft_answer": None,
        "citations": [],
        "grounding_score": None,
        "revise_count": 0,
        "approval": "auto",
        "published": False,
        "step_log": [],
        "next": "END",
    }


SAMPLE_QUERY = (
    "What torque specification applies to part PN-4421 on the Osaka assembly line?"
)


if __name__ == "__main__":
    graph = build_graph()
    state = make_initial_state(thread_id="demo-q-e01", query=SAMPLE_QUERY)
    config = {"configurable": {"thread_id": "demo-q-e01"}}

    print(f"Processing query ({state['role']}): {state['query']}\n")
    for update in graph.stream(state, config, stream_mode="updates"):
        for node_name, node_update in update.items():
            if node_update.get("step_log"):
                print(f"  [{node_name}] {node_update['step_log'][-1]}")
            if node_update.get("next"):
                print(f"  [{node_name}] next={node_update['next']}")

    final = graph.get_state(config).values
    print(
        f"\nDone — published={final['published']}, domain={final['domain']}, "
        f"grounding={final['grounding_score']}"
    )
    print(f"Total steps: {len(final['step_log'])}")
