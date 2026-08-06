"""Hybrid search — Chroma dense + BM25 with RRF fusion."""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CHROMA = ROOT / "data" / "chroma"
COLLECTION_NAME = "bankshield_chunks"

EMPTY_CHUNK = {
    "id": "EMPTY",
    "text": "",
    "score": 0.0,
    "metadata": {"domain": "empty", "source": "empty"},
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", (text or "").lower())


def _bm25_scores(query: str, documents: list[str], k1: float = 1.5, b: float = 0.75) -> list[float]:
    tokenized = [_tokenize(d) for d in documents]
    q_tokens = _tokenize(query)
    if not q_tokens or not tokenized:
        return [0.0] * len(documents)
    n = len(tokenized)
    avgdl = sum(len(t) for t in tokenized) / n
    df: Counter[str] = Counter()
    for toks in tokenized:
        df.update(set(toks))
    scores: list[float] = []
    for toks in tokenized:
        tf = Counter(toks)
        dl = len(toks) or 1
        score = 0.0
        for term in q_tokens:
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            numer = tf[term] * (k1 + 1)
            denom = tf[term] + k1 * (1 - b + b * dl / avgdl)
            score += idf * numer / denom
        scores.append(score)
    return scores


def _rrf(rank_lists: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranks in rank_lists:
        for i, doc_id in enumerate(ranks):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + i + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def hybrid_search(
    query: str,
    *,
    domain: str | None = None,
    k: int = 6,
) -> list[dict[str, Any]]:
    """Dense + BM25 hybrid retrieval from local Chroma."""
    import chromadb

    from app.llm import get_embeddings

    persist = Path(os.getenv("BANKSHIELD_CHROMA_DIR") or DEFAULT_CHROMA)
    client = chromadb.PersistentClient(path=str(persist))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    total = collection.count()
    if total == 0:
        return []

    fetch_n = min(max(k * 4, 20), total)
    emb = get_embeddings().embed_query(query)
    dense = collection.query(
        query_embeddings=[emb],
        n_results=fetch_n,
        include=["documents", "metadatas", "distances"],
    )

    all_ids = dense.get("ids", [[]])[0]
    all_docs = dense.get("documents", [[]])[0]
    all_metas = dense.get("metadatas", [[]])[0]
    all_dists = dense.get("distances", [[]])[0]

    got = collection.get(include=["documents", "metadatas"])
    id_to_doc = dict(zip(got["ids"], got["documents"] or [], strict=False))
    id_to_meta = dict(zip(got["ids"], got["metadatas"] or [], strict=False))

    bm25_ids = list(id_to_doc.keys())
    bm25_texts = [id_to_doc[i] or "" for i in bm25_ids]
    bm25 = _bm25_scores(query, bm25_texts)
    bm25_ranked = [
        i for i, _ in sorted(zip(bm25_ids, bm25, strict=True), key=lambda x: x[1], reverse=True)
    ]
    dense_ranked = list(all_ids)
    fused = _rrf([dense_ranked, bm25_ranked])
    dense_score = {i: (1.0 / (1.0 + float(d))) for i, d in zip(all_ids, all_dists, strict=False)}

    out: list[dict[str, Any]] = []
    for doc_id, rrf_score in fused:
        meta = dict(id_to_meta.get(doc_id) or {})
        if domain and str(meta.get("domain", "")) not in ("", domain):
            if meta.get("domain"):
                continue
        text = id_to_doc.get(doc_id) or ""
        out.append(
            {
                "id": doc_id,
                "text": text,
                "score": float(rrf_score + dense_score.get(doc_id, 0.0)),
                "metadata": meta,
            }
        )
        if len(out) >= k:
            break
    return out


def rerank_chunks(query: str, candidates: list[dict], n: int = 5) -> list[dict]:
    """Simple lexical rerank on top of hybrid fusion."""
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return candidates[:n]

    def _score(item: dict) -> float:
        toks = set(_tokenize(item.get("text") or ""))
        overlap = len(q_tokens & toks) / max(len(q_tokens), 1)
        return float(item.get("score") or 0.0) + overlap

    return sorted(candidates, key=_score, reverse=True)[:n]
