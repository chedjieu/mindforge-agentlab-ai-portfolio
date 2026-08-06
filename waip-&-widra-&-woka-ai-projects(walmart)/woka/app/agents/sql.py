"""SQL Agent — structured queries over mock supply-chain schema."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.db import get_connection, ping as db_ping

ROOT = Path(__file__).resolve().parents[2]
SEED_FALLBACK = ROOT / "data" / "sql_seeds" / "uc1_fallback.json"


def _fallback_payload() -> dict[str, Any]:
    if SEED_FALLBACK.exists():
        return json.loads(SEED_FALLBACK.read_text(encoding="utf-8"))
    return {
        "closed_dcs": [
            {"dc_id": "ATL-01", "name": "Atlanta DC", "region": "SE", "status": "closed"},
            {"dc_id": "JAX-02", "name": "Jacksonville DC", "region": "SE", "status": "closed"},
        ],
        "delayed_shipments": [
            {"shipment_id": "SH-9001", "supplier_id": "SUP-ACME", "sku": "TV-55-4K", "dest_dc": "ATL-01", "eta_hours": 72},
            {"shipment_id": "SH-9002", "supplier_id": "SUP-GULF", "sku": "MILK-GAL", "dest_dc": "JAX-02", "eta_hours": 36},
        ],
        "inventory_within_300mi": [
            {"location_id": "MEM-03", "sku": "TV-55-4K", "qty": 12400},
            {"location_id": "MEM-03", "sku": "MILK-GAL", "qty": 8200},
            {"location_id": "MEM-03", "sku": "WATER-24", "qty": 15000},
        ],
        "alt_sourcing_contracts": [
            {"contract_id": "C-ACME-2024", "supplier_id": "SUP-ACME", "allows_alt_source": True, "notice_hours": 48},
            {"contract_id": "C-GULF-2023", "supplier_id": "SUP-GULF", "allows_alt_source": True, "notice_hours": 48},
        ],
        "stockout_risk_48h": [
            {"store_id": "S-1001", "sku": "MILK-GAL", "qty": 40},
            {"store_id": "S-1044", "sku": "MILK-GAL", "qty": 25},
        ],
        "affected_suppliers": [
            {"supplier_id": "SUP-ACME", "name": "Acme Logistics"},
            {"supplier_id": "SUP-GULF", "name": "GulfFresh Produce"},
        ],
    }


def _query_postgres() -> dict[str, Any]:
    with get_connection() as conn:
        closed = conn.execute(
            "SELECT dc_id, name, region, status FROM dcs WHERE status = 'closed'"
        ).fetchall()
        delayed = conn.execute(
            """
            SELECT shipment_id, supplier_id, sku, dest_dc, status, eta_hours
            FROM shipments WHERE status = 'delayed'
            """
        ).fetchall()
        inv = conn.execute(
            """
            SELECT location_id, sku, qty FROM inventory
            WHERE location_type = 'dc' AND location_id IN (
              SELECT dc_id FROM dcs WHERE status = 'open' AND region = 'SE'
            )
            """
        ).fetchall()
        contracts = conn.execute(
            """
            SELECT contract_id, supplier_id, allows_alt_source, notice_hours, confidentiality
            FROM contracts WHERE allows_alt_source = TRUE AND confidentiality = 'internal'
            """
        ).fetchall()
        stockout = conn.execute(
            """
            SELECT store_id, sku, qty FROM inventory
            WHERE location_type = 'store' AND sku = 'MILK-GAL' AND qty < 50
            """
        ).fetchall()
        suppliers = conn.execute(
            """
            SELECT DISTINCT s.supplier_id, s.name
            FROM suppliers s
            JOIN shipments sh ON sh.supplier_id = s.supplier_id
            WHERE sh.status = 'delayed'
            """
        ).fetchall()

    return {
        "closed_dcs": [
            {"dc_id": r[0], "name": r[1], "region": r[2], "status": r[3]} for r in closed
        ],
        "delayed_shipments": [
            {
                "shipment_id": r[0],
                "supplier_id": r[1],
                "sku": r[2],
                "dest_dc": r[3],
                "status": r[4],
                "eta_hours": r[5],
            }
            for r in delayed
        ],
        "inventory_within_300mi": [
            {"location_id": r[0], "sku": r[1], "qty": r[2]} for r in inv
        ],
        "alt_sourcing_contracts": [
            {
                "contract_id": r[0],
                "supplier_id": r[1],
                "allows_alt_source": bool(r[2]),
                "notice_hours": r[3],
                "confidentiality": r[4],
            }
            for r in contracts
        ],
        "stockout_risk_48h": [
            {"store_id": r[0], "sku": r[1], "qty": r[2]} for r in stockout
        ],
        "affected_suppliers": [
            {"supplier_id": r[0], "name": r[1]} for r in suppliers
        ],
    }


def run_sql_agent(query: str, *, region: str = "SE") -> dict[str, Any]:
    """Answer UC-1 structured questions via deterministic SQL (mock schema)."""
    try:
        payload = _query_postgres() if db_ping() else _fallback_payload()
        backend = "postgres" if db_ping() else "fallback"
    except Exception as exc:  # noqa: BLE001
        payload = _fallback_payload()
        backend = f"fallback:{exc}"

    summary_bits = [
        f"Closed DCs: {', '.join(d['dc_id'] for d in payload['closed_dcs']) or 'none'}",
        f"Affected suppliers: {', '.join(s['name'] for s in payload['affected_suppliers']) or 'none'}",
        f"Alt-source contracts: {', '.join(c['contract_id'] for c in payload['alt_sourcing_contracts']) or 'none'}",
        f"Backup inventory (open SE DCs): "
        + ", ".join(f"{i['sku']}@{i['location_id']}={i['qty']}" for i in payload["inventory_within_300mi"][:6]),
        f"48h stockout risk: "
        + ", ".join(f"{s['store_id']}/{s['sku']}={s['qty']}" for s in payload["stockout_risk_48h"])
        or "none",
    ]
    return {
        "agent": "sql",
        "backend": backend,
        "region": region,
        "query": query,
        "data": payload,
        "summary": " | ".join(summary_bits),
        "citations": [
            {
                "doc_id": "sql:inventory",
                "title": "Inventory / shipments SQL",
                "page": 0,
                "section": "query",
                "snippet": summary_bits[3],
                "confidence": 0.97,
                "source_type": "sql",
            },
            {
                "doc_id": "sql:contracts",
                "title": "Alternate sourcing contracts",
                "page": 0,
                "section": "query",
                "snippet": summary_bits[2],
                "confidence": 0.96,
                "source_type": "sql",
            },
        ],
    }
