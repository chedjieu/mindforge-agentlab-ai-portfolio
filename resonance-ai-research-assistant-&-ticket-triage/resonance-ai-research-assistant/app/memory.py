"""Memory store for the research assistant (Day 5 H2).

Wraps LangGraph's InMemoryStore or PostgresStore depending on `RAIRA_MEMORY`.
Provides recall() and remember() helpers used by graph nodes.
"""

from __future__ import annotations

import os
from typing import Literal
from uuid import uuid4

from langgraph.store.base import BaseStore


def get_store() -> BaseStore:
    """Return the configured memory store (singleton-ish via module cache).

    RAIRA_MEMORY=memory  -> InMemoryStore (default, no persistence)
    RAIRA_MEMORY=postgres -> PostgresStore backed by POSTGRES_DSN
    """
    backend = os.getenv("RAIRA_MEMORY", "memory").strip().lower()

    if backend == "postgres":
        from langgraph.store.postgres import PostgresStore

        dsn = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5433/resonance")
        store = PostgresStore.from_conn_string(dsn)
        store.setup()
        return store

    from langgraph.store.memory import InMemoryStore

    return InMemoryStore()


def recall(store: BaseStore, namespace: tuple[str, ...], query: str, k: int = 3) -> list[dict]:
    """Search the store for top-k memories matching query."""
    items = store.search(namespace, query=query, limit=k)
    return [
        {
            "key": item.key,
            "value": item.value,
            "score": getattr(item, "score", None),
        }
        for item in items
    ]


def remember(
    store: BaseStore,
    namespace: tuple[str, ...],
    content: str,
    kind: Literal["preference", "fact"],
) -> None:
    """Write a memory to the store with an auto-generated key."""
    key = str(uuid4())
    store.put(
        namespace,
        key,
        {"content": content, "kind": kind},
    )


__all__ = ["get_store", "recall", "remember"]
