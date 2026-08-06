"""Retriever worker — hybrid search + rerank."""

from __future__ import annotations

from app.state import KnowledgeState
from app.tools.hybrid_search import hybrid_search
from app.tools.rerank import EMPTY_CHUNK, rerank_chunks


def retriever_node(state: KnowledgeState) -> dict:
    query = state.get("query") or ""
    domain = state.get("domain")
    role = state.get("role") or "engineer"

    try:
        candidates = hybrid_search(query=query, domain=domain, role=role, k=8)
    except Exception as exc:
        candidates = []
        err = f"hybrid_search error: {exc}"
    else:
        err = None

    if not candidates:
        q_trunc = query.replace("\n", " ")[:80]
        msg = f"retriever: EMPTY (q={q_trunc!r}"
        if err:
            msg += f", {err}"
        msg += ")"
        return {
            "retrieved_chunks": [dict(EMPTY_CHUNK)],
            "step_log": state["step_log"] + [msg],
        }

    ranked = rerank_chunks(query, candidates, n=5)
    if not ranked:
        ranked = [dict(EMPTY_CHUNK)]

    top_ids = [c.get("chunk_id", "?") for c in ranked[:5]]
    q_trunc = query.replace("\n", " ")[:80]
    return {
        "retrieved_chunks": ranked,
        "step_log": state["step_log"]
        + [f"retriever: q={q_trunc!r} top={top_ids}"],
    }
