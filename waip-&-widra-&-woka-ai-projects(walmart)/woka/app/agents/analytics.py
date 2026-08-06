"""Analytics Agent — stub KPI summary for UC-1."""

from __future__ import annotations

from typing import Any


def run_analytics_agent(sql: dict[str, Any] | None = None) -> dict[str, Any]:
    data = (sql or {}).get("data") or {}
    kpis = {
        "closed_dc_count": len(data.get("closed_dcs") or []),
        "delayed_shipment_count": len(data.get("delayed_shipments") or []),
        "alt_contract_count": len(data.get("alt_sourcing_contracts") or []),
        "stockout_store_sku_pairs": len(data.get("stockout_risk_48h") or []),
        "backup_inventory_lines": len(data.get("inventory_within_300mi") or []),
    }
    return {
        "agent": "analytics",
        "kpis": kpis,
        "summary": (
            f"{kpis['closed_dc_count']} DCs closed, {kpis['delayed_shipment_count']} delayed shipments, "
            f"{kpis['stockout_store_sku_pairs']} store/SKU pairs at 48h stockout risk."
        ),
    }
