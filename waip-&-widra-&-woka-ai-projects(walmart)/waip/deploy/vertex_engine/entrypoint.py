"""Vertex AI Agent Engine entrypoint — wraps WAIP graph."""

from __future__ import annotations

import os
from typing import Any


def query(payload: dict[str, Any]) -> dict[str, Any]:
    os.environ.setdefault("WAIP_MODEL", os.getenv("WAIP_MODEL", "fake"))
    from langgraph.types import Command
    import uuid
    from app.graph import build_graph_with_backends
    from app.main import _load_abac

    graph = build_graph_with_backends()
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    associate_id = payload.get("associate_id", "A1001")
    init = {
        "associate_id": associate_id,
        "abac": _load_abac(associate_id),
        "query": payload.get("query", ""),
        "step_log": [],
        "evidence": [],
        "worker_results": {},
        "ticket_ids": [],
    }
    result = graph.invoke(init, config=thread)
    if graph.get_state(thread).tasks and payload.get("auto_approve", True):
        result = graph.invoke(Command(resume={"approved": True, "note": "vertex"}), config=thread)
    return {
        "final_response": result.get("final_response"),
        "ticket_ids": result.get("ticket_ids"),
        "citations": result.get("citations"),
        "judges": result.get("judges"),
        "runtime": "vertex-agent-engine",
    }


if __name__ == "__main__":
    print(query({"query": "Am I eligible for dental benefits?", "associate_id": "A1001"}))
