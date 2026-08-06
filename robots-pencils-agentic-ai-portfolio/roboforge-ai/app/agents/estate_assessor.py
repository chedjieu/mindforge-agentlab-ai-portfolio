"""Estate assessor — cloud + legacy mocks."""

from __future__ import annotations

from app.tools.estate import assess_cloud_inventory, assess_legacy_apps
from app.state import ForgeState


def estate_assessor_node(state: ForgeState) -> dict:
    client_id = state["client_id"]
    domain = state.get("domain") or "agentic"
    cloud = assess_cloud_inventory(client_id=client_id, domain=domain)
    legacy = assess_legacy_apps(client_id=client_id, domain=domain)
    estate = {
        "cloud": cloud,
        "legacy": legacy,
        "modernization_score": round(
            (cloud.get("readiness_score", 0.5) + legacy.get("modernization_score", 0.5)) / 2, 2
        ),
        "notes": "Mock inventories only — no live cloud APIs in v1",
    }
    return {
        "estate": estate,
        "step_log": state["step_log"]
        + [f"estate_assessor: score={estate['modernization_score']}"],
    }
