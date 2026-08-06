"""Semantic memory — per-tenant facts via LangGraph Store (in-memory fallback)."""

from __future__ import annotations

from typing import Any

# Process-local fallback when no Store is injected
_TENANT_FACTS: dict[str, dict[str, Any]] = {
    "tenant-asu-demo": {
        "client_voice": "academic, clarity-first",
        "cloud": "AWS",
        "notes": "Canvas enrollment modernization context",
    },
    "tenant-careco": {
        "client_voice": "clinical-trust, concise",
        "cloud": "AWS",
        "notes": "HIPAA care-ops triage",
    },
    "tenant-northbank": {
        "client_voice": "formal, risk-averse",
        "cloud": "AWS",
        "notes": "GLBA account-ops",
    },
}


def recall_tenant(tenant_id: str, store=None) -> dict:
    if store is not None:
        try:
            items = store.search(("tenant", tenant_id), query=tenant_id, limit=5)
            facts = {}
            for it in items or []:
                val = getattr(it, "value", None) or it
                if isinstance(val, dict):
                    facts.update(val)
            if facts:
                return facts
        except Exception:
            pass
    return dict(_TENANT_FACTS.get(tenant_id, {"notes": "no semantic facts yet"}))


def remember_tenant(tenant_id: str, facts: dict, store=None) -> None:
    if store is not None:
        try:
            store.put(("tenant", tenant_id), tenant_id, facts)
            return
        except Exception:
            pass
    existing = _TENANT_FACTS.get(tenant_id, {})
    existing.update(facts)
    _TENANT_FACTS[tenant_id] = existing
