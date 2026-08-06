"""AWS Bedrock AgentCore entrypoint for panasonic-egkp.

Lives at the project root so AgentCore (Linux ARM64) receives a posix-safe
entrypoint path. Nested Windows paths like deploy\\file.py break packaging.
"""

from __future__ import annotations

import os

from bedrock_agentcore import BedrockAgentCoreApp
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore

from app.graph import build_graph_with_backends

app = BedrockAgentCoreApp()


@app.entrypoint
async def handler(payload, context):
    dsn = os.environ["POSTGRES_DSN"]
    with (
        PostgresSaver.from_conn_string(dsn) as saver,
        PostgresStore.from_conn_string(dsn) as store,
    ):
        saver.setup()
        store.setup()
        graph = build_graph_with_backends(saver=saver, store=store)
        config = {"configurable": {"thread_id": context.session_id}}
        async for event in graph.astream_events(payload, config=config, version="v2"):
            await app.streaming.write(event)
