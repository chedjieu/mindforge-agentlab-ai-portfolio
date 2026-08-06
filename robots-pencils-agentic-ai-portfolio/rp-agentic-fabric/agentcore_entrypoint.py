"""Bedrock AgentCore entrypoint for R&P Agentic Delivery Fabric."""

from __future__ import annotations

import json
import os
from typing import Any

# Disable AgentCore managed memory by default (matches AS_BUILT)
os.environ.setdefault("DISABLE_AGENTCORE_MEMORY", "1")

from app.graph import build_graph_with_backends, make_initial_state


def _saver():
    dsn = os.getenv("POSTGRES_DSN", "").strip()
    if dsn:
        from langgraph.checkpoint.postgres import PostgresSaver

        return PostgresSaver.from_conn_string(dsn)
    import sqlite3
    from pathlib import Path

    from langgraph.checkpoint.sqlite import SqliteSaver

    path = Path(__file__).resolve().parent.parent / "checkpoints.sqlite"
    conn = sqlite3.connect(str(path), check_same_thread=False)
    return SqliteSaver(conn)


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """AgentCore-compatible handler.

    Event shape:
      {"engagement_id": "...", "tenant_id": "...", "brief": {...}, "thread_id": "..."}
    """
    brief = event.get("brief") or event.get("raw_brief") or {}
    tenant_id = event.get("tenant_id") or "tenant-default"
    engagement_id = event.get("engagement_id") or brief.get("id") or "ENG-UNKNOWN"
    thread_id = event.get("thread_id") or engagement_id

    graph = build_graph_with_backends(_saver())
    state = make_initial_state(str(engagement_id), brief, tenant_id)
    config = {"configurable": {"thread_id": str(thread_id)}}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    final = graph.get_state(config).values
    return {
        "engagement_id": engagement_id,
        "tenant_id": tenant_id,
        "vertical": final.get("vertical"),
        "published": final.get("published"),
        "audit_pack_id": final.get("audit_pack_id"),
        "approval": final.get("approval"),
        "judge_scores": final.get("judge_scores"),
        "step_log": final.get("step_log"),
    }


# Optional AgentCore app object
try:
    from bedrock_agentcore.runtime import BedrockAgentCoreApp

    app = BedrockAgentCoreApp()

    @app.entrypoint
    def agentcore_entry(payload: dict) -> dict:
        if isinstance(payload, str):
            payload = json.loads(payload)
        return handler(payload)

except Exception:  # pragma: no cover
    app = None
