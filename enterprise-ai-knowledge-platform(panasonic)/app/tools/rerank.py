"""Rerank retrieved chunks (LLM when available; token overlap for fake)."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app._fake_llm import is_fake_chat_model
from app.llm import get_chat_model, invoke_with_throttle_fallback


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", (text or "").lower()))


def _overlap_score(query: str, text: str) -> float:
    q = _tokenize(query)
    if not q:
        return 0.0
    t = _tokenize(text)
    if not t:
        return 0.0
    return len(q & t) / len(q)


def _fake_rerank(query: str, chunks: list[dict], n: int) -> list[dict]:
    scored: list[tuple[float, dict]] = []
    for ch in chunks:
        score = _overlap_score(query, ch.get("text") or "")
        enriched = dict(ch)
        meta = dict(enriched.get("metadata") or {})
        meta["rerank_score"] = score
        meta["rerank"] = "token_overlap"
        enriched["metadata"] = meta
        enriched["score"] = score
        scored.append((score, enriched))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:n]]


def _llm_rerank(query: str, chunks: list[dict], n: int) -> list[dict]:
    """Ask the chat model for an ordered list of chunk_ids."""
    catalog = [
        {
            "chunk_id": c.get("chunk_id"),
            "doc_id": c.get("doc_id"),
            "text": (c.get("text") or "")[:400],
        }
        for c in chunks
    ]
    prompt = (
        "Rerank candidate chunks for the user query. "
        f"Return JSON only: {{\"ordered_ids\": [\"chunk_id\", ...]}} "
        f"with at most {n} ids, best first.\n\n"
        f"Query: {query}\n\nCandidates:\n{json.dumps(catalog, ensure_ascii=False)}"
    )

    def _call() -> str:
        model = get_chat_model()
        msg = model.invoke(
            [
                SystemMessage(content="You are a careful retrieval reranker."),
                HumanMessage(content=prompt),
            ]
        )
        content = msg.content
        return content if isinstance(content, str) else json.dumps(content)

    raw = invoke_with_throttle_fallback(_call)
    try:
        # tolerate fenced JSON
        m = re.search(r"\{.*\}", raw, flags=re.S)
        data = json.loads(m.group(0) if m else raw)
        ordered = list(data.get("ordered_ids") or [])
    except Exception:
        return _fake_rerank(query, chunks, n)

    by_id = {c.get("chunk_id"): c for c in chunks}
    out: list[dict] = []
    for i, cid in enumerate(ordered):
        if cid not in by_id:
            continue
        enriched = dict(by_id[cid])
        meta = dict(enriched.get("metadata") or {})
        meta["rerank_score"] = float(n - i)
        meta["rerank"] = "llm"
        enriched["metadata"] = meta
        enriched["score"] = float(n - i)
        out.append(enriched)
        if len(out) >= n:
            break

    # Append any missing chunks by overlap so we still fill n when possible
    if len(out) < n:
        seen = {c["chunk_id"] for c in out}
        for c in _fake_rerank(query, chunks, len(chunks)):
            if c.get("chunk_id") in seen:
                continue
            out.append(c)
            if len(out) >= n:
                break
    return out[:n]


def rerank_chunks(query: str, chunks: list[dict], n: int = 5) -> list[dict]:
    """Rerank chunks; fake/unset model uses token overlap, else LLM JSON order."""
    if not chunks:
        return []
    n = max(1, min(n, len(chunks)))
    model_name = (os.getenv("EGKP_MODEL") or "").strip()
    # Unset or explicit fake → deterministic overlap (offline / CI).
    if not model_name or is_fake_chat_model(model_name):
        return _fake_rerank(query, chunks, n)
    try:
        return _llm_rerank(query, chunks, n)
    except Exception:
        return _fake_rerank(query, chunks, n)


EMPTY_CHUNK: dict[str, Any] = {
    "chunk_id": "EMPTY",
    "doc_id": "",
    "text": "",
    "score": 0.0,
    "metadata": {"empty": True},
}
