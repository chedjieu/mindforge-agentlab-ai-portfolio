"""Hybrid BM25 + dense retrieval."""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any

from app.llm import get_embeddings

ROOT = Path(__file__).resolve().parents[2]
SEARCH_DIRS = [
    ROOT / "data" / "corpus",
    ROOT / "data" / "policies",
    ROOT / "data" / "guidelines",
    ROOT / "data" / "formulary",
    ROOT / "data" / "pathways",
]
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def _load_chunks() -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for folder in SEARCH_DIRS:
        if not folder.exists():
            continue
        for path in sorted(folder.glob("**/*")):
            if path.suffix.lower() not in {".md", ".txt"}:
                continue
            text = path.read_text(encoding="utf-8")
            domain = path.parent.name
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


def _bm25(query: str, docs: list[dict[str, Any]]) -> list[float]:
    q = _tokenize(query)
    if not q or not docs:
        return [0.0] * len(docs)
    toks = [_tokenize(d["text"]) for d in docs]
    N = len(docs)
    avgdl = sum(len(t) for t in toks) / max(N, 1)
    df: dict[str, int] = {}
    for tlist in toks:
        for t in set(tlist):
            df[t] = df.get(t, 0) + 1
    scores = []
    for tlist in toks:
        tf: dict[str, int] = {}
        for t in tlist:
            tf[t] = tf.get(t, 0) + 1
        score = 0.0
        dl = len(tlist) or 1
        for qt in q:
            if qt not in tf:
                continue
            n_q = df.get(qt, 0) or 1
            idf = math.log(1 + (N - n_q + 0.5) / (n_q + 0.5))
            score += idf * (tf[qt] * 2.2) / (tf[qt] + 1.2 * (0.25 + 0.75 * dl / avgdl))
        scores.append(score)
    return scores


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


def hybrid_search(query: str, limit: int = 6, folder: str | None = None) -> list[dict[str, Any]]:
    docs = _load_chunks()
    if folder:
        filtered = [d for d in docs if d.get("domain") == folder]
        if filtered:
            docs = filtered
    if not docs:
        return []
    bm25 = _bm25(query, docs)
    emb = get_embeddings()
    qv = emb.embed_query(query)
    dvs = emb.embed_documents([d["text"] for d in docs])
    dense = [_cos(qv, v) for v in dvs]
    max_b = max(bm25) or 1.0
    fused = []
    for i, doc in enumerate(docs):
        score = 0.55 * (bm25[i] / max_b) + 0.45 * dense[i]
        fused.append((score, {**doc, "score": round(score, 4)}))
    fused.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in fused[:limit]]
