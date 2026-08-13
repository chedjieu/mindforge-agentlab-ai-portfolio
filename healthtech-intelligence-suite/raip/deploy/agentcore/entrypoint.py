"""Bedrock AgentCore-shaped entrypoint (sketch)."""

from __future__ import annotations

from app.orchestration.graph import build_graph_with_backends
from app.orchestration.state import make_initial_state


def handler(event: dict, _context: object | None = None) -> dict:
    graph = build_graph_with_backends()
    state = make_initial_state(
        request_id=str(event.get("request_id", "agentcore")),
        thread_id=str(event.get("thread_id", "agentcore")),
        tenant_id=str(event.get("tenant_id", "tenant-northstar")),
        user_id=str(event.get("user_id", "author-01")),
        project_id=str(event.get("project_id", "tenant-northstar-proj-golden")),
        query=str(event.get("query", "Draft the Clinical Management Recommendations section.")),
    )
    result = graph.invoke(state, {"configurable": {"thread_id": state["thread_id"]}})
    return {"draft": result.get("draft"), "workflow_status": result.get("workflow_status")}
