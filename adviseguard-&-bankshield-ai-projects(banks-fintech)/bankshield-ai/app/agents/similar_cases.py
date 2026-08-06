"""Similar historical case retrieval via vector search."""

from __future__ import annotations

from app.state import InvestigationState
from app.tools.hybrid_search import hybrid_search, rerank_chunks


def similar_cases_node(state: InvestigationState) -> dict:
    alert = state.get("alert") or {}
    fraud_types = state.get("fraud_types") or []
    query = (
        f"historical investigation {' '.join(fraud_types)} "
        f"{alert.get('description', '')} amount={alert.get('amount')}"
    )
    hits = hybrid_search(query, domain="closed_cases", k=6)
    if not hits:
        hits = hybrid_search(query, domain="sar_examples", k=6)
    ranked = rerank_chunks(query, hits, n=4) if hits else []

    # Sentinel
    if not ranked:
        ranked = [
            {
                "id": "case-none",
                "text": "No closely matching closed cases in the local index.",
                "score": 0.0,
                "metadata": {"domain": "closed_cases"},
            }
        ]

    evidence = list(state.get("evidence") or [])
    evidence.append(
        {
            "id": "similar-cases",
            "source": "similar_cases",
            "summary": f"Matched {len(ranked)} prior cases/SAR notes",
            "case_ids": [h.get("id") for h in ranked],
        }
    )
    return {
        "similar_cases": ranked,
        "evidence": evidence,
        "step_log": state["step_log"] + [f"SimilarCases: n={len(ranked)}"],
    }
