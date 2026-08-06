"""Engagement fabric LangGraph — supervisor routes workers in a loop."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore

from app.agents.audit_publish import audit_publish_node
from app.agents.compliance_mapper import compliance_mapper_node
from app.agents.engagement_synthesizer import engagement_synthesizer_node
from app.agents.hitl import hitl_node
from app.agents.judge_gate import judge_gate_node
from app.agents.retrieval import retrieval_node
from app.agents.reuse_broker import reuse_broker_node
from app.agents.supervisor import supervisor_node
from app.agents.vertical_router import vertical_router_node
from app.state import EngagementState

CHECKPOINT_PATH = Path(__file__).resolve().parent.parent / "checkpoints.sqlite"


def build_graph_with_backends(saver: Any, store: BaseStore | None = None):
    """Compile the fabric graph with injected checkpoint saver and store."""
    builder = StateGraph(EngagementState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("vertical_router", vertical_router_node)
    builder.add_node("compliance_mapper", compliance_mapper_node)
    builder.add_node("reuse_broker", reuse_broker_node)
    builder.add_node("retrieval", retrieval_node)
    builder.add_node("engagement_synthesizer", engagement_synthesizer_node)
    builder.add_node("judge_gate", judge_gate_node)
    builder.add_node("hitl", hitl_node)
    builder.add_node("audit_publish", audit_publish_node)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state["next"],
        {
            "vertical_router": "vertical_router",
            "compliance_mapper": "compliance_mapper",
            "reuse_broker": "reuse_broker",
            "retrieval": "retrieval",
            "engagement_synthesizer": "engagement_synthesizer",
            "judge_gate": "judge_gate",
            "hitl": "hitl",
            "audit_publish": "audit_publish",
            "END": END,
        },
    )
    for worker in (
        "vertical_router",
        "compliance_mapper",
        "reuse_broker",
        "retrieval",
        "engagement_synthesizer",
        "judge_gate",
        "hitl",
        "audit_publish",
    ):
        builder.add_edge(worker, "supervisor")

    return builder.compile(checkpointer=saver, store=store)


def build_graph():
    """Compile with a SqliteSaver checkpointer (local dev)."""
    conn = sqlite3.connect(str(CHECKPOINT_PATH), check_same_thread=False)
    return build_graph_with_backends(SqliteSaver(conn))


def make_initial_state(engagement_id: str, raw_brief: dict, tenant_id: str) -> EngagementState:
    return {
        "engagement_id": engagement_id,
        "tenant_id": tenant_id,
        "raw_brief": raw_brief,
        "vertical": None,
        "sensitivity": None,
        "policy_pack_id": None,
        "guardrail_config": None,
        "reuse_decided": False,
        "reuse_decisions": [],
        "evidence": [],
        "draft_plan": None,
        "judge_scores": None,
        "approval": "pending",
        "published": False,
        "audit_pack_id": None,
        "step_log": [],
        "next": "END",
    }


SAMPLE_BRIEF = {
    "id": "ENG-1001",
    "title": "FERPA-safe student onboarding agent",
    "body": (
        "Build a multi-agent student onboarding flow for our Canvas/SIS stack. "
        "Must respect FERPA, reuse R&P edtech onboarding playbook IP, and produce "
        "an audit pack for university security review before go-live."
    ),
    "constraints": "No cross-tenant data; Slack HITL for production promote",
    "client": "ASU Demo University",
}

SAMPLE_TENANT = "tenant-asu-demo"


if __name__ == "__main__":
    import os

    from langgraph.types import Command

    os.environ.setdefault("RPADF_MODEL", "fake")
    graph = build_graph()
    state = make_initial_state("ENG-1001", SAMPLE_BRIEF, SAMPLE_TENANT)
    config = {"configurable": {"thread_id": "demo-eng-1001"}}

    print(f"Processing engagement {state['engagement_id']} ({state['tenant_id']})\n")
    for update in graph.stream(state, config, stream_mode="updates"):
        for node_name, node_update in update.items():
            if isinstance(node_update, dict) and node_update.get("step_log"):
                print(f"  [{node_name}] {node_update['step_log'][-1]}")

    snap = graph.get_state(config)
    pending = any(getattr(t, "interrupts", None) for t in (snap.tasks or ()))
    if pending:
        print("  [hitl] interrupt — auto-approving for CLI demo")
        for update in graph.stream(
            Command(resume={"action": "approve", "edited_body": None}),
            config,
            stream_mode="updates",
        ):
            for node_name, node_update in update.items():
                if isinstance(node_update, dict) and node_update.get("step_log"):
                    print(f"  [{node_name}] {node_update['step_log'][-1]}")

    final = graph.get_state(config).values
    print(
        f"\nDone — published={final.get('published')}, "
        f"vertical={final.get('vertical')}, approval={final.get('approval')}, "
        f"audit={final.get('audit_pack_id')}"
    )
    print(f"Total steps: {len(final.get('step_log') or [])}")
