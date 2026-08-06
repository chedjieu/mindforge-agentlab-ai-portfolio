"""Hybrid search — Chroma (default), Bedrock KB, or Vertex Vector Search."""

from __future__ import annotations

import json
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CHROMA = ROOT / "data" / "chroma"
COLLECTION_NAME = "egkp_chunks"


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


def _parse_acl(meta: dict[str, Any]) -> list[str]:
    raw = meta.get("acl_roles")
    if isinstance(raw, list):
        return [str(x) for x in raw]
    if isinstance(raw, str) and raw.strip():
        try:
            val = json.loads(raw)
            if isinstance(val, list):
                return [str(x) for x in val]
        except json.JSONDecodeError:
            return [p.strip() for p in raw.split(",") if p.strip()]
    return []


def _acl_allows(role: str, meta: dict[str, Any]) -> bool:
    acl = _parse_acl(meta)
    if not acl:
        return True
    return role in acl


def _filter_results(
    results: list[dict],
    *,
    domain: str | None,
    role: str,
    k: int,
) -> list[dict]:
    out: list[dict] = []
    for item in results:
        meta = dict(item.get("metadata") or {})
        if domain and str(meta.get("domain", "")) not in ("", domain):
            # Allow missing domain from cloud backends
            if meta.get("domain"):
                continue
        if not _acl_allows(role, meta):
            continue
        meta["acl_roles"] = _parse_acl(meta)
        item = {**item, "metadata": meta}
        out.append(item)
        if len(out) >= k:
            break
    return out


def _search_chroma(
    query: str,
    domain: str | None,
    role: str,
    k: int,
) -> list[dict]:
    import chromadb

    from app.llm import get_embeddings

    persist = Path(os.getenv("EGKP_CHROMA_DIR") or DEFAULT_CHROMA)
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

    if total <= 500:
        got = collection.get(include=["documents", "metadatas"])
        id_to_doc = dict(zip(got["ids"], got["documents"] or [], strict=False))
        id_to_meta = dict(zip(got["ids"], got["metadatas"] or [], strict=False))
    else:
        id_to_doc = dict(zip(all_ids, all_docs, strict=False))
        id_to_meta = dict(zip(all_ids, all_metas, strict=False))

    bm25_ids = list(id_to_doc.keys())
    bm25_texts = [id_to_doc[i] or "" for i in bm25_ids]
    bm25 = _bm25_scores(query, bm25_texts)
    bm25_ranked = [
        i for i, _ in sorted(zip(bm25_ids, bm25, strict=True), key=lambda x: x[1], reverse=True)
    ]
    dense_ranked = list(all_ids)
    fused = _rrf([dense_ranked, bm25_ranked])
    dense_score = {
        i: (1.0 / (1.0 + float(d))) for i, d in zip(all_ids, all_dists, strict=False)
    }
    bm25_map = dict(zip(bm25_ids, bm25, strict=False))

    results: list[dict] = []
    for chunk_id, rrf_score in fused:
        meta = dict(id_to_meta.get(chunk_id) or {})
        text = id_to_doc.get(chunk_id) or ""
        results.append(
            {
                "chunk_id": chunk_id,
                "doc_id": meta.get("doc_id", ""),
                "text": text,
                "score": float(rrf_score),
                "metadata": {
                    **meta,
                    "dense_score": dense_score.get(chunk_id, 0.0),
                    "bm25_score": bm25_map.get(chunk_id, 0.0),
                    "backend": "chroma",
                },
            }
        )
    return _filter_results(results, domain=domain, role=role, k=k)


def _search_bedrock_kb(
    query: str,
    domain: str | None,
    role: str,
    k: int,
) -> list[dict]:
    """Query AWS Bedrock Knowledge Bases; same return schema as Chroma path."""
    kb_id = os.getenv("BEDROCK_KB_ID", "").strip()
    if not kb_id:
        raise RuntimeError("EGKP_VECTORS=bedrock_kb requires BEDROCK_KB_ID")

    import boto3

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    client = boto3.client("bedrock-agent-runtime", region_name=region)
    resp = client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": query},
        retrievalConfiguration={
            "vectorSearchConfiguration": {"numberOfResults": max(k, 8)}
        },
    )
    results: list[dict] = []
    for i, item in enumerate(resp.get("retrievalResults") or []):
        content = (item.get("content") or {}).get("text") or ""
        score = float(item.get("score") or 0.0)
        loc = item.get("location") or {}
        doc_id = (
            (loc.get("s3Location") or {}).get("uri")
            or (loc.get("webLocation") or {}).get("url")
            or f"bedrock-kb-{i}"
        )
        meta = {
            "domain": domain or "",
            "acl_roles": [],
            "backend": "bedrock_kb",
            "location": loc,
        }
        # Optional metadata attributes from KB
        for attr in item.get("metadata") or {}:
            if isinstance(attr, dict) and "key" in attr:
                meta[str(attr["key"])] = attr.get("value")
        results.append(
            {
                "chunk_id": f"bedrock::{i}::{hash(content) & 0xFFFF:x}",
                "doc_id": str(doc_id),
                "text": content,
                "score": score,
                "metadata": meta,
            }
        )
    return _filter_results(results, domain=domain, role=role, k=k)


def _search_vertex(
    query: str,
    domain: str | None,
    role: str,
    k: int,
) -> list[dict]:
    """Thin Vertex AI Vector Search adapter — same return schema as Chroma."""
    project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GCP_LOCATION") or os.getenv("VERTEX_LOCATION") or "us-central1"
    index_endpoint = os.getenv("VERTEX_INDEX_ENDPOINT", "").strip()
    deployed_index = os.getenv("VERTEX_DEPLOYED_INDEX_ID", "").strip()
    if not project or not index_endpoint or not deployed_index:
        raise RuntimeError(
            "EGKP_VECTORS=vertex requires GCP_PROJECT, VERTEX_INDEX_ENDPOINT, "
            "VERTEX_DEPLOYED_INDEX_ID"
        )

    from google.cloud import aiplatform
    from app.llm import get_embeddings

    aiplatform.init(project=project, location=location)
    endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=index_endpoint)
    emb = get_embeddings().embed_query(query)
    response = endpoint.find_neighbors(
        deployed_index_id=deployed_index,
        queries=[emb],
        num_neighbors=max(k, 8),
    )
    results: list[dict] = []
    neighbors = response[0] if response else []
    for i, n in enumerate(neighbors):
        # MatchingEngine neighbor API varies by SDK version
        nid = getattr(n, "id", None) or getattr(n, "datapoint_id", None) or f"vertex-{i}"
        dist = getattr(n, "distance", None)
        score = 1.0 / (1.0 + float(dist)) if dist is not None else float(getattr(n, "score", 0.0) or 0.0)
        restricts = getattr(n, "restricts", None) or []
        meta: dict[str, Any] = {"backend": "vertex", "acl_roles": [], "domain": domain or ""}
        text = str(getattr(n, "crowding_tag", "") or "")
        # Prefer embedding datapoint crowding / restricts for metadata if present
        for r in restricts:
            ns = getattr(r, "namespace", None) or (r.get("namespace") if isinstance(r, dict) else None)
            allow = getattr(r, "allow_list", None) or (r.get("allow_list") if isinstance(r, dict) else None)
            if ns:
                meta[str(ns)] = list(allow or [])
        results.append(
            {
                "chunk_id": str(nid),
                "doc_id": str(meta.get("doc_id") or nid),
                "text": text or f"(vertex neighbor {nid})",
                "score": score,
                "metadata": meta,
            }
        )
    return _filter_results(results, domain=domain, role=role, k=k)


def hybrid_search(
    query: str,
    domain: str | None = None,
    role: str = "engineer",
    k: int = 8,
) -> list[dict]:
    """Retrieve chunks. Backend selected by EGKP_VECTORS (default chroma)."""
    backend = (os.getenv("EGKP_VECTORS") or "chroma").strip().lower()
    if backend == "bedrock_kb":
        return _search_bedrock_kb(query, domain, role, k)
    if backend == "vertex":
        return _search_vertex(query, domain, role, k)
    # chroma (default) and unknown → local hybrid
    return _search_chroma(query, domain, role, k)
