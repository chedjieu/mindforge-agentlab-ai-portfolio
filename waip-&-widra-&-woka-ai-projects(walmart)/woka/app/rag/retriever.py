"""Hybrid retrieval: BM25 + dense + ACL pre-filter + light rerank."""

from __future__ import annotations

import math
import re
from typing import Any

from app.llm import get_embeddings
from app.rag.store import IndexedChunk, load_index
from app.security.acl import AccessScope, chunk_authorized


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9\-]+", text.lower()) if len(t) > 1}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


def _bm25_score(query_tokens: set[str], doc_tokens: set[str], avgdl: float, df: dict[str, int], n: int) -> float:
    score = 0.0
    dl = max(len(doc_tokens), 1)
    k1, b = 1.2, 0.75
    for t in query_tokens:
        if t not in doc_tokens:
            continue
        n_q = df.get(t, 0) or 1
        idf = math.log(1 + (n - n_q + 0.5) / (n_q + 0.5))
        tf = 1.0
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    return score


def hybrid_search(
    query: str,
    scope: AccessScope,
    *,
    top_k: int = 5,
    force_reload: bool = False,
) -> list[dict[str, Any]]:
    """ACL-filtered hybrid search. Authorization happens before scoring."""
    corpus = load_index(force=force_reload)
    allowed = [
        c
        for c in corpus
        if chunk_authorized(
            scope,
            acl_policy_name=c.acl_policy_name,
            confidentiality=c.confidentiality,
            region=c.region,
        )
    ]
    if not allowed:
        return []

    q_tokens = _tokenize(query)
    q_vec = get_embeddings().embed_query(query)
    n = len(allowed)
    avgdl = sum(len(c.tokens) for c in allowed) / max(n, 1)
    df: dict[str, int] = {}
    for c in allowed:
        for t in c.tokens:
            df[t] = df.get(t, 0) + 1

    scored: list[tuple[float, IndexedChunk]] = []
    for c in allowed:
        bm = _bm25_score(q_tokens, c.tokens, avgdl, df, n)
        dense = _cosine(q_vec, c.vector)
        # Weighted fusion ~ 0.3 BM25 + 0.7 dense via RRF-style mix
        score = 0.3 * (bm / (1.0 + bm)) + 0.7 * dense
        for boost in ("hurricane", "supplier", "inventory", "contract", "stockout", "dc", "sku"):
            if boost in q_tokens and boost in c.tokens:
                score += 0.03
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    reranked = sorted(
        scored[: max(top_k * 4, top_k)],
        key=lambda x: (x[0] + 0.015 * len(q_tokens & _tokenize(x[1].title + " " + x[1].filename))),
        reverse=True,
    )[:top_k]

    return [
        {
            "chunk_id": c.chunk_id,
            "doc_id": c.doc_id,
            "title": c.title,
            "text": c.text,
            "page": c.page_start,
            "section": c.metadata.get("section_heading", ""),
            "score": round(score, 4),
            "acl_policy_name": c.acl_policy_name,
            "department": c.department,
            "region": c.region,
            "confidentiality": c.confidentiality,
            "filename": c.filename,
        }
        for score, c in reranked
    ]
