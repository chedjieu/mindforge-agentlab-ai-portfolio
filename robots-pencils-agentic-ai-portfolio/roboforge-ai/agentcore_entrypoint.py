"""AgentCore entrypoint scaffold."""

from __future__ import annotations

import os
from typing import Any

os.environ.setdefault("DISABLE_AGENTCORE_MEMORY", "1")

from app.graph import build_graph_with_backends, make_initial_state


def _saver():
    import sqlite3
    from pathlib import Path

    from langgraph.checkpoint.sqlite import SqliteSaver

    path = Path(__file__).resolve().parent / "checkpoints.sqlite"
    return SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))


def handler(event: dict[str, Any], context: Any = None) -> dict:
    pack = event.get("pack") or event.get("raw_pack") or {}
    client_id = event.get("client_id") or "client-default"
    engagement_id = event.get("engagement_id") or pack.get("id") or "RF-UNKNOWN"
    graph = build_graph_with_backends(_saver())
    state = make_initial_state(str(engagement_id), pack, client_id)
    config = {"configurable": {"thread_id": str(engagement_id)}}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    final = graph.get_state(config).values
    return {
        "domain": final.get("domain"),
        "published": final.get("published"),
        "delivery_pack_id": final.get("delivery_pack_id"),
        "approval": final.get("approval"),
        "judge_scores": final.get("judge_scores"),
    }


try:
    from bedrock_agentcore.runtime import BedrockAgentCoreApp

    app = BedrockAgentCoreApp()

    @app.entrypoint
    def agentcore_entry(payload: dict) -> dict:
        return handler(payload if isinstance(payload, dict) else {})

except Exception:
    app = None
