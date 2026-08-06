"""Retrieval Agent — hybrid search + GraphRAG within security scope."""

from __future__ import annotations

from typing import Any

from app.rag.kg import graph_hops
from app.rag.retriever import hybrid_search
from app.security.acl import AccessScope


def run_retrieval_agent(
    query: str,
    scope: AccessScope,
    *,
    top_k: int = 5,
    include_graph: bool = True,
) -> dict[str, Any]:
    chunks = hybrid_search(query, scope, top_k=top_k)
    graph = graph_hops(query, limit=8) if include_graph else []
    return {
        "agent": "retrieval",
        "query": query,
        "chunks": chunks,
        "graph_facts": graph,
        "chunk_count": len(chunks),
        "graph_count": len(graph),
        "scope_policies": scope.allowed_policies,
    }
