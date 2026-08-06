"""Regulatory RAG + fixture live intel worker."""

from __future__ import annotations

from pathlib import Path

from app.state import InvestigationState
from app.tools.hybrid_search import EMPTY_CHUNK, hybrid_search, rerank_chunks

ROOT = Path(__file__).resolve().parent.parent.parent
LIVE_FEEDS = ROOT / "data" / "corpus" / "ofac_guidance" / "live_feed_fixture.md"


def regulatory_rag_node(state: InvestigationState) -> dict:
    alert = state.get("alert") or {}
    fraud_types = state.get("fraud_types") or []
    query = (
        state.get("query")
        or f"AML OFAC requirements for {', '.join(fraud_types)} "
        f"{alert.get('description', '')} {alert.get('beneficiary_country', '')}"
    )

    domains = ["aml_policy", "ofac_guidance", "fraud_playbooks"]
    candidates: list[dict] = []
    for domain in domains:
        candidates.extend(hybrid_search(query, domain=domain, k=4))

    # Deduplicate by id
    seen = set()
    uniq = []
    for c in candidates:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        uniq.append(c)

    ranked = rerank_chunks(query, uniq, n=5) if uniq else []

    # Fixture "live online search"
    live_bits: list[dict] = []
    if LIVE_FEEDS.exists():
        text = LIVE_FEEDS.read_text(encoding="utf-8")
        live_bits.append(
            {
                "id": "live-ofac-feed",
                "text": text[:1200],
                "score": 0.7,
                "metadata": {"domain": "ofac_guidance", "source": "live_feed_fixture"},
            }
        )

    citations = ranked + live_bits
    if not citations:
        citations = [dict(EMPTY_CHUNK)]

    evidence = list(state.get("evidence") or [])
    evidence.append(
        {
            "id": "reg-rag",
            "source": "regulatory_rag",
            "summary": f"Retrieved {len(citations)} regulatory/intel snippets",
            "doc_ids": [c.get("id") for c in citations if c.get("id") != "EMPTY"],
        }
    )

    return {
        "reg_citations": citations,
        "evidence": evidence,
        "step_log": state["step_log"] + [f"RegulatoryRAG: citations={len(citations)}"],
    }
