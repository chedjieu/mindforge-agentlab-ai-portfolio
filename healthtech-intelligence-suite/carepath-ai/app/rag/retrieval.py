"""Hybrid BM25-style + dense retrieval over data/corpus."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from app.llm import get_embeddings

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus"

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def _load_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    if not CORPUS.exists():
        return chunks
    for path in sorted(CORPUS.glob("**/*")):
        if path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        text = path.read_text(encoding="utf-8")
        domain = path.stem.split("_")[0] if "_" in path.stem else "general"
        # split on headings / blank lines
        parts = re.split(r"\n#{1,3}\s+|\n\n+", text)
        for i, part in enumerate(parts):
            part = part.strip()
            if len(part) < 40:
                continue
            chunks.append(
                {
                    "id": f"{path.stem}-{i}",
                    "source": path.name,
                    "domain": domain,
                    "text": part[:1200],
                }
            )
    return chunks


def _bm25_scores(query: str, docs: list[dict[str, Any]], k1: float = 1.2, b: float = 0.75) -> list[float]:
    q_tokens = _tokenize(query)
    if not q_tokens or not docs:
        return [0.0] * len(docs)
    doc_tokens = [_tokenize(d["text"]) for d in docs]
    N = len(docs)
    avgdl = sum(len(t) for t in doc_tokens) / max(N, 1)
    df: dict[str, int] = {}
    for toks in doc_tokens:
        for t in set(toks):
            df[t] = df.get(t, 0) + 1
    scores: list[float] = []
    for toks in doc_tokens:
        tf: dict[str, int] = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        dl = len(toks) or 1
        for qt in q_tokens:
            if qt not in tf:
                continue
            n_q = df.get(qt, 0) or 1
            idf = math.log(1 + (N - n_q + 0.5) / (n_q + 0.5))
            denom = tf[qt] + k1 * (1 - b + b * dl / avgdl)
            score += idf * (tf[qt] * (k1 + 1)) / denom
        scores.append(score)
    return scores


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


def hybrid_search(query: str, limit: int = 6, domain: str | None = None) -> list[dict[str, Any]]:
    docs = _load_chunks()
    if domain:
        filtered = [d for d in docs if d.get("domain") == domain]
        if filtered:
            docs = filtered
    if not docs:
        return []

    bm25 = _bm25_scores(query, docs)
    emb = get_embeddings()
    q_vec = emb.embed_query(query)
    d_vecs = emb.embed_documents([d["text"] for d in docs])
    dense = [_cosine(q_vec, v) for v in d_vecs]

    # normalize bm25
    max_b = max(bm25) or 1.0
    fused: list[tuple[float, dict[str, Any]]] = []
    for i, doc in enumerate(docs):
        score = 0.55 * (bm25[i] / max_b) + 0.45 * dense[i]
        fused.append((score, {**doc, "score": round(score, 4)}))
    fused.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in fused[:limit]]
