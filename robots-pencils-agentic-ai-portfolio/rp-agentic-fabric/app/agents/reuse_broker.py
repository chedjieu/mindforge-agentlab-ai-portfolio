"""Reuse broker — sanitize reusable IP components before tenant RAG."""

from __future__ import annotations

from app.tools.kg import list_reusable_components, sanitize_component
from app.state import EngagementState


def reuse_broker_node(state: EngagementState) -> dict:
    vertical = state["vertical"] or "edtech"
    tenant_id = state["tenant_id"]
    candidates = list_reusable_components(vertical=vertical, exclude_tenant=tenant_id)
    decisions: list[dict] = []
    for comp in candidates[:5]:
        sanitized = sanitize_component(comp, for_tenant=tenant_id)
        decisions.append(sanitized)

    return {
        "reuse_decided": True,
        "reuse_decisions": decisions,
        "step_log": state["step_log"]
        + [f"reuse_broker: sanitized {len(decisions)} component(s) for {tenant_id}"],
    }
