"""Hybrid retrieval: BM25 + dense + metadata + GraphRAG neighborhood + RRF + rerank."""

from __future__ import annotations

import json
import re
from collections import defaultdict

import numpy as np
from rank_bm25 import BM25Okapi

from app.graph.store import graph_store
from app.llm import get_embeddings
from app.models.contracts import TIER_RANK, EvidencePassage
from app.storage.schema import DocumentRow, DocumentVersionRow, EvidenceChunkRow

_TOKEN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def cosine(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def rrf_fuse(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    scores: dict[str, float] = defaultdict(float)
    for ranking in rankings:
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] += 1.0 / (k + rank)
    return dict(scores)


def _emb(chunk: EvidenceChunkRow) -> list[float]:
    try:
        return json.loads(chunk.embedding_json or "[]")
    except json.JSONDecodeError:
        return []


def retrieve(
    query: str,
    chunks: list[EvidenceChunkRow],
    documents: dict[str, DocumentRow],
    versions: dict[str, DocumentVersionRow],
    *,
    tenant_id: str,
    top_k: int = 12,
    exclude_superseded: bool = True,
) -> list[EvidencePassage]:
    if not chunks:
        return []
    superseded: set[str] = set()
    g = graph_store()
    for version_row in versions.values():
        if version_row.supersedes_version_id:
            superseded |= g.superseded_version_ids(tenant_id, version_row.id)
            superseded.add(version_row.supersedes_version_id)
    pool = [c for c in chunks if not (exclude_superseded and c.version_id in superseded)]
    if not pool:
        pool = list(chunks)

    tokenized = [tokenize(c.text) for c in pool]
    bm25 = BM25Okapi(tokenized) if tokenized else None
    q_tokens = tokenize(query)
    bm25_scores = list(bm25.get_scores(q_tokens)) if bm25 is not None else [0.0] * len(pool)
    bm25_order = [pool[i].id for i in np.argsort(bm25_scores)[::-1]]

    q_emb = get_embeddings().embed_query(query)
    dense_scores = [cosine(q_emb, _emb(c)) for c in pool]
    dense_order = [pool[i].id for i in np.argsort(dense_scores)[::-1]]

    fused = rrf_fuse([bm25_order, dense_order])
    # Authority prior: boost higher-tier sources (lower rank number).
    for c in pool:
        tier = TIER_RANK.get(c.authority_tier, 6)
        fused[c.id] = fused.get(c.id, 0) + 0.05 * (7 - tier)

    # Parent expansion: if a child ranks high, include its PARENT:: section sibling.
    ranked_ids = sorted(fused, key=lambda i: fused[i], reverse=True)
    by_id = {c.id: c for c in pool}
    expanded: list[str] = []
    seen: set[str] = set()
    for cid in ranked_ids:
        if cid in seen:
            continue
        expanded.append(cid)
        seen.add(cid)
        child = by_id.get(cid)
        if child and not child.section.startswith("PARENT::"):
            for other in pool:
                if other.section == f"PARENT::{child.section}" and other.id not in seen:
                    expanded.append(other.id)
                    seen.add(other.id)

    # GraphRAG: neighborhood of top chunks (same version sections).
    for cid in expanded[:5]:
        for nb in g.neighbors(tenant_id, cid, "SECTION_CONTAINS_CHUNK"):
            if nb not in seen and nb in by_id:
                expanded.append(nb)
                seen.add(nb)

    out: list[EvidencePassage] = []
    bm25_map = {pool[i].id: float(bm25_scores[i]) for i in range(len(pool))}
    dense_map = {pool[i].id: float(dense_scores[i]) for i in range(len(pool))}
    for cid in expanded[: top_k * 2]:
        c = by_id[cid]
        doc = documents.get(c.document_id)
        ver: DocumentVersionRow | None = versions.get(c.version_id)
        score = fused.get(cid, 0.0)
        # Heuristic rerank: lexical overlap + authority + recency-ish effective_date.
        overlap = len(set(q_tokens) & set(tokenize(c.text))) / max(1, len(set(q_tokens)))
        rerank = 0.5 * score + 0.3 * overlap + 0.2 * (c.authority_score or 0)
        method = "hybrid+rrf"
        if dense_map.get(cid, 0) > bm25_map.get(cid, 0) / (max(bm25_scores) or 1):
            method = "dense+hybrid"
        out.append(
            EvidencePassage(
                chunk_id=c.id,
                document_id=c.document_id,
                version_id=c.version_id,
                version_number=ver.version_number if ver else "",
                title=doc.title if doc else "",
                page_number=c.page_number,
                section=c.section,
                parent_section=c.parent_section,
                text=c.text,
                authority_tier=c.authority_tier,
                authority_score=c.authority_score,
                effective_date=c.effective_date or None,
                superseded=c.version_id in superseded,
                retrieval_method=method,
                score=rerank,
                checksum=c.checksum,
            )
        )
    out.sort(key=lambda p: p.score, reverse=True)
    return out[:top_k]


def lexical_overlap(a: str, b: str) -> float:
    sa, sb = set(tokenize(a)), set(tokenize(b))
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
