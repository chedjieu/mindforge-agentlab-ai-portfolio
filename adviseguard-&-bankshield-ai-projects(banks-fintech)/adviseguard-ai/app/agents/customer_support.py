"""Customer support specialist — grounded FAQ / account assist."""

from __future__ import annotations

from app.state import SessionState


def customer_support_node(state: SessionState) -> dict:
    chunks = [
        c
        for c in (state.get("retrieved_chunks") or [])
        if c.get("id") not in (None, "EMPTY")
        and str(c.get("metadata", {}).get("domain", "")) in ("support_kb", "products", "")
    ]
    if not chunks:
        chunks = [c for c in (state.get("retrieved_chunks") or []) if c.get("id") != "EMPTY"][:3]
    citations = [c.get("id") for c in chunks[:4]]
    body = " ".join((c.get("text") or "")[:280] for c in chunks[:2]) or (
        "I can help with account questions. Please see the support knowledge base."
    )
    answer = {
        "summary": body[:700],
        "citations": citations,
        "customer_id": state.get("customer_id"),
        "resolved": bool(chunks),
    }
    return {
        "support_answer": answer,
        "step_log": state["step_log"] + [f"Support: citations={len(citations)}"],
    }
