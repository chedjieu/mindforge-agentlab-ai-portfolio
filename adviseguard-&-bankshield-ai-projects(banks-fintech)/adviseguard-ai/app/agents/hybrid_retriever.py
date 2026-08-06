"""Hybrid RAG retriever + fixture live market/fraud feed."""

from __future__ import annotations

from pathlib import Path

from app.state import SessionState
from app.tools.hybrid_search import EMPTY_CHUNK, hybrid_search, rerank_chunks

ROOT = Path(__file__).resolve().parent.parent.parent
LIVE_FEED = ROOT / "data" / "corpus" / "market_fixture" / "live_feed.md"


def hybrid_retriever_node(state: SessionState) -> dict:
    intent = state.get("intent") or "support"
    query = state.get("query") or ""
    domains = {
        "advice": ["advice_playbooks", "products", "regulations", "market_fixture"],
        "fraud": ["fraud_patterns", "regulations", "market_fixture"],
        "support": ["support_kb", "products"],
        "mixed": [
            "advice_playbooks",
            "products",
            "fraud_patterns",
            "support_kb",
            "regulations",
            "market_fixture",
        ],
    }.get(intent, ["support_kb", "regulations"])

    candidates: list[dict] = []
    for domain in domains:
        candidates.extend(hybrid_search(query, domain=domain, k=4))

    seen: set[str] = set()
    uniq = []
    for c in candidates:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        uniq.append(c)
    ranked = rerank_chunks(query, uniq, n=6) if uniq else []

    if LIVE_FEED.exists():
        ranked.append(
            {
                "id": "live-market-feed",
                "text": LIVE_FEED.read_text(encoding="utf-8")[:1200],
                "score": 0.65,
                "metadata": {"domain": "market_fixture", "source": "live_feed"},
            }
        )
    if not ranked:
        ranked = [dict(EMPTY_CHUNK)]

    return {
        "retrieved_chunks": ranked,
        "step_log": state["step_log"] + [f"HybridRetriever: chunks={len(ranked)}"],
    }
