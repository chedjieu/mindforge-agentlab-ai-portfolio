"""Bedrock AgentCore entrypoint — wraps WAIP graph."""

from __future__ import annotations

import os
from typing import Any


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """AgentCore-compatible invoke wrapper.

    Expects event: {associate_id, query, auto_approve?}
    """
    os.environ.setdefault("WAIP_MODEL", os.getenv("WAIP_MODEL", "fake"))
    from langgraph.types import Command
    import uuid
    from app.graph import build_graph_with_backends
    from app.main import _load_abac

    graph = build_graph_with_backends()
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    associate_id = event.get("associate_id", "A1001")
    init = {
        "associate_id": associate_id,
        "abac": _load_abac(associate_id),
        "query": event.get("query", ""),
        "step_log": [],
        "evidence": [],
        "worker_results": {},
        "ticket_ids": [],
    }
    result = graph.invoke(init, config=thread)
    if graph.get_state(thread).tasks and event.get("auto_approve", True):
        result = graph.invoke(Command(resume={"approved": True, "note": "agentcore"}), config=thread)
    return {
        "final_response": result.get("final_response"),
        "ticket_ids": result.get("ticket_ids"),
        "citations": result.get("citations"),
        "judges": result.get("judges"),
        "runtime": "bedrock-agentcore",
    }


if __name__ == "__main__":
    print(handler({"query": "What is FMLA?", "associate_id": "A1001", "auto_approve": True}))
