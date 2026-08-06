"""MCP-shaped enterprise tool mocks (Workday, ServiceNow, Leave, SAP)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "data" / "profiles"
TICKETS = ROOT / "data" / "tickets.jsonl"


def _load_profile(associate_id: str) -> dict[str, Any]:
    path = PROFILES / f"{associate_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    # default
    return {
        "associate_id": associate_id,
        "name": "Demo Associate",
        "country": "US",
        "state": "AR",
        "store": "1001",
        "department": "Pharmacy",
        "role": "Pharmacy Tech",
        "bu": "US Stores",
    }


def workday_get_pay_stub(associate_id: str, abac: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = _load_profile(associate_id)
    return {
        "system": "workday",
        "associate_id": associate_id,
        "pay_period": "2026-07-06..2026-07-12",
        "gross_pay": 820.0,
        "net_pay": 612.40,
        "regular_hours": 32.0,
        "leave_unpaid_hours": 8.0,
        "overtime_hours": 0.0,
        "notes": "8 unpaid medical leave hours excluded from regular pay",
        "country": profile.get("country"),
    }


def workday_get_hours(associate_id: str, abac: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "system": "workday",
        "associate_id": associate_id,
        "hours": [
            {"date": "2026-07-06", "type": "regular", "hours": 8},
            {"date": "2026-07-07", "type": "regular", "hours": 8},
            {"date": "2026-07-08", "type": "medical_leave_unpaid", "hours": 8},
            {"date": "2026-07-09", "type": "regular", "hours": 8},
            {"date": "2026-07-10", "type": "regular", "hours": 8},
        ],
    }


def leave_get_balances(associate_id: str, abac: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "system": "leave",
        "associate_id": associate_id,
        "pto_hours": 46.0,
        "sick_hours": 12.0,
        "fmla_available": True,
        "recent_leave": [
            {
                "type": "medical_leave",
                "start": "2026-07-08",
                "end": "2026-07-08",
                "paid": False,
                "status": "approved",
            }
        ],
    }


def leave_check_fmla(associate_id: str, abac: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = _load_profile(associate_id)
    return {
        "system": "leave",
        "associate_id": associate_id,
        "eligible": profile.get("country") == "US",
        "reason": "US associate with qualifying tenure (demo)",
        "state": profile.get("state"),
    }


def sap_get_cost_center(associate_id: str, abac: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = _load_profile(associate_id)
    return {
        "system": "sap",
        "associate_id": associate_id,
        "cost_center": f"CC-{profile.get('store', '0000')}",
        "company_code": "US01",
    }


def servicenow_create_incident(
    associate_id: str,
    short_description: str,
    description: str,
    abac: dict[str, Any] | None = None,
) -> dict[str, Any]:
    TICKETS.parent.mkdir(parents=True, exist_ok=True)
    seq = 1000
    if TICKETS.exists():
        seq += sum(1 for _ in TICKETS.open(encoding="utf-8"))
    ticket_id = f"INC{seq:07d}"
    row = {
        "ticket_id": ticket_id,
        "associate_id": associate_id,
        "short_description": short_description,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "open",
        "assignment_group": "Payroll Ops",
        "abac": abac or {},
    }
    with TICKETS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row


def servicenow_get_incident(ticket_id: str) -> dict[str, Any] | None:
    if not TICKETS.exists():
        return None
    for line in TICKETS.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("ticket_id") == ticket_id:
            return row
    return None


# MCP-style tool registry for agents
TOOL_SPECS = {
    "workday.get_pay_stub": workday_get_pay_stub,
    "workday.get_hours": workday_get_hours,
    "leave.get_balances": leave_get_balances,
    "leave.check_fmla": leave_check_fmla,
    "sap.get_cost_center": sap_get_cost_center,
    "servicenow.create_incident": servicenow_create_incident,
    "servicenow.get_incident": servicenow_get_incident,
}
