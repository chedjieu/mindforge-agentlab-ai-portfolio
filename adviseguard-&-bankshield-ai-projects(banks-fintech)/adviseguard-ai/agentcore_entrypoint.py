"""Bedrock AgentCore entrypoint stub."""

from __future__ import annotations

import os

from app.graph import build_graph as local_build
from app.graph import build_graph_with_backends, make_initial_state


def build_graph():
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        return local_build()
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.store.memory import InMemoryStore

    saver = PostgresSaver.from_conn_string(dsn)
    store = None if os.getenv("DISABLE_AGENTCORE_MEMORY", "1") == "1" else InMemoryStore()
    return build_graph_with_backends(saver, store=store)


__all__ = ["build_graph", "make_initial_state"]
