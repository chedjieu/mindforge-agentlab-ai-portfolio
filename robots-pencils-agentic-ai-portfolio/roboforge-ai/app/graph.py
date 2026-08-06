"""RoboForge LangGraph."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore

from app.agents.delivery_publish import delivery_publish_node
from app.agents.estate_assessor import estate_assessor_node
from app.agents.hitl import hitl_node
from app.agents.intake_analyzer import intake_analyzer_node
from app.agents.judge_gate import judge_gate_node
from app.agents.knowledge_builder import knowledge_builder_node
from app.agents.roi_optimizer import roi_optimizer_node
from app.agents.security_compliance import security_compliance_node
from app.agents.solution_architect import solution_architect_node
from app.agents.supervisor import supervisor_node
from app.state import ForgeState

CHECKPOINT_PATH = Path(__file__).resolve().parent.parent / "checkpoints.sqlite"


def build_graph_with_backends(saver: Any, store: BaseStore | None = None):
    builder = StateGraph(ForgeState)
    nodes = {
        "supervisor": supervisor_node,
        "intake_analyzer": intake_analyzer_node,
        "estate_assessor": estate_assessor_node,
        "knowledge_builder": knowledge_builder_node,
        "security_compliance": security_compliance_node,
        "solution_architect": solution_architect_node,
        "roi_optimizer": roi_optimizer_node,
        "judge_gate": judge_gate_node,
        "hitl": hitl_node,
        "delivery_publish": delivery_publish_node,
    }
    for name, fn in nodes.items():
        builder.add_node(name, fn)
    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        lambda s: s["next"],
        {**{k: k for k in nodes if k != "supervisor"}, "END": END},
    )
    for worker in nodes:
        if worker != "supervisor":
            builder.add_edge(worker, "supervisor")
    return builder.compile(checkpointer=saver, store=store)


def build_graph():
    conn = sqlite3.connect(str(CHECKPOINT_PATH), check_same_thread=False)
    return build_graph_with_backends(SqliteSaver(conn))


def make_initial_state(engagement_id: str, raw_pack: dict, client_id: str) -> ForgeState:
    return {
        "engagement_id": engagement_id,
        "client_id": client_id,
        "raw_pack": raw_pack,
        "domain": None,
        "intake": None,
        "estate": None,
        "evidence": [],
        "security_findings": None,
        "blueprint": None,
        "roi": None,
        "judge_scores": None,
        "approval": "pending",
        "published": False,
        "delivery_pack_id": None,
        "step_log": [],
        "next": "END",
    }


SAMPLE_PACK = {
    "id": "RF-1001",
    "title": "RetailCo agentic customer-ops on Bedrock AgentCore",
    "body": (
        "Design a multi-agent customer-ops system on Amazon Bedrock and AgentCore. "
        "Include hybrid RAG, GraphRAG for order dependencies, HITL before production, "
        "and ROI for a Velocity Pod delivery."
    ),
    "constraints": "AWS-first; Slack HITL; no live PII",
    "documents": ["architecture-notes.md", "security-policy.md"],
}
SAMPLE_CLIENT = "client-retailco"


if __name__ == "__main__":
    import os

    from langgraph.types import Command

    os.environ.setdefault("RFAI_MODEL", "fake")
    graph = build_graph()
    state = make_initial_state("RF-1001", SAMPLE_PACK, SAMPLE_CLIENT)
    config = {"configurable": {"thread_id": "demo-rf-1001"}}
    print(f"Processing {state['engagement_id']} ({state['client_id']})\n")
    for update in graph.stream(state, config, stream_mode="updates"):
        for node_name, node_update in update.items():
            if isinstance(node_update, dict) and node_update.get("step_log"):
                print(f"  [{node_name}] {node_update['step_log'][-1]}")

    snap = graph.get_state(config)
    if any(getattr(t, "interrupts", None) for t in (snap.tasks or ())):
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
        f"\nDone — published={final.get('published')} domain={final.get('domain')} "
        f"pack={final.get('delivery_pack_id')}"
    )
