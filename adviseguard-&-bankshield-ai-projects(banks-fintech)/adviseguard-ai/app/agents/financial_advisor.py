"""Financial advisor — personalized product / plan recommendations."""

from __future__ import annotations

from app.state import SessionState


PRODUCT_MAP = {
    "conservative": ("AG-BOND-CORE", "Core Bond Fund — capital preservation focus"),
    "moderate": ("AG-BALANCED-60", "Balanced 60/40 Portfolio"),
    "aggressive": ("AG-GROWTH-EQ", "Growth Equity Sleeve"),
}


def financial_advisor_node(state: SessionState) -> dict:
    profile = state.get("customer_profile") or {}
    goals = state.get("goals") or profile.get("goals") or ["retirement"]
    risk = (state.get("risk_tolerance") or profile.get("risk_tolerance") or "moderate").lower()
    if risk not in PRODUCT_MAP:
        risk = "moderate"
    product_id, product_name = PRODUCT_MAP[risk]
    chunks = state.get("retrieved_chunks") or []
    citations = [c.get("id") for c in chunks if c.get("id") not in (None, "EMPTY")][:5]
    graph = state.get("graph_paths") or []
    suitable = any("SUITABLE_FOR" in (p.get("relationships") or []) for p in graph)

    draft = {
        "product_id": product_id,
        "product_name": product_name,
        "risk_tolerance": risk,
        "goals": goals,
        "summary": (
            f"Based on goals {goals} and {risk} risk tolerance, recommend {product_name} "
            f"({product_id}). This is educational guidance only; outcomes can vary."
        ),
        "citations": citations,
        "graph_supported": suitable or bool(graph),
        "high_stakes": risk == "aggressive" or "retirement" in [str(g).lower() for g in goals],
        "disclaimer": "Past performance does not predict future results. Investments involve risk.",
    }
    return {
        "advice_draft": draft,
        "goals": list(goals),
        "risk_tolerance": risk,
        "step_log": state["step_log"]
        + [f"Advisor: product={product_id} risk={risk} high_stakes={draft['high_stakes']}"],
    }
