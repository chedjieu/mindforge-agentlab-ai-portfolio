"""Generate NDA-safe synthetic corpus + KG seeds for panasonic-egkp demos."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus"
KG = ROOT / "data" / "kg"


def _fm(
    *,
    doc_id: str,
    domain: str,
    doc_type: str,
    plant: str,
    acl_roles: list[str],
    effective_date: str,
    supersedes: str | None,
    entities: list[str],
) -> str:
    roles = "[" + ", ".join(acl_roles) + "]"
    ents = "[" + ", ".join(entities) + "]"
    sup = supersedes if supersedes else ""
    return (
        "---\n"
        f"doc_id: {doc_id}\n"
        f"domain: {domain}\n"
        f"doc_type: {doc_type}\n"
        f"plant: {plant}\n"
        f"acl_roles: {roles}\n"
        f"effective_date: {effective_date}\n"
        f"supersedes: {sup}\n"
        f"entities: {ents}\n"
        "---\n"
    )


def _write(domain: str, filename: str, frontmatter: str, body: str) -> None:
    path = CORPUS / domain / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter + "\n" + body.strip() + "\n", encoding="utf-8")


def write_manufacturing() -> None:
    domain = "manufacturing"
    roles = ["engineer", "manufacturing", "quality"]
    docs = [
        (
            "SOP-M-104-torque-assembly.md",
            _fm(
                doc_id="SOP-M-104",
                domain=domain,
                doc_type="sop",
                plant="Osaka",
                acl_roles=roles,
                effective_date="2024-01-15",
                supersedes=None,
                entities=["PN-4421", "Plant-Osaka", "SOP-M-104"],
            ),
            """
# SOP-M-104 Torque Assembly (superseded)

## Purpose
Legacy torque procedure for battery tray fastener PN-4421.

## Torque specification
Apply **10 N·m ± 1.0** using calibrated torque wrench TW-Osaka-12.

## Notes
This document is superseded by SOP-M-105. Do not use for new builds after 2025-06-01.
""",
        ),
        (
            "SOP-M-105-torque-assembly-v2.md",
            _fm(
                doc_id="SOP-M-105",
                domain=domain,
                doc_type="sop",
                plant="Osaka",
                acl_roles=roles,
                effective_date="2025-06-01",
                supersedes="SOP-M-104",
                entities=["PN-4421", "Plant-Osaka", "SOP-M-105", "BOM-BAT-TRAY"],
            ),
            """
# SOP-M-105 Torque Assembly v2

## Purpose
Current torque procedure for battery tray fastener **PN-4421** at Plant Osaka.

## Torque specification
Apply **12 N·m ± 0.5** using calibrated torque wrench TW-Osaka-12.
Record reading in MES form MFG-TORQUE-01.

## Sequence
1. Verify PN-4421 lot is released by Quality.
2. Seat fastener flush against BOM-BAT-TRAY bracket.
3. Torque to 12 N·m ± 0.5.
4. Mark fastener with blue lacquer.

## Supersession
This SOP supersedes SOP-M-104.
""",
        ),
        (
            "PLANT-OSAKA-line-safety.md",
            _fm(
                doc_id="PLANT-OSAKA-SAFE",
                domain=domain,
                doc_type="safety",
                plant="Osaka",
                acl_roles=roles + ["safety"],
                effective_date="2025-03-01",
                supersedes=None,
                entities=["Plant-Osaka", "Line-A3"],
            ),
            """
# Plant Osaka Line A3 Safety

## Lockout
Energy isolation required before tooling changes on Line-A3.
Wear cut-resistant gloves when handling PN-4421 trays.

## Attribution
Safety phrasing paraphrased for training; not an official OSHA publication.
""",
        ),
        (
            "SOP-M-210-cell-insertion.md",
            _fm(
                doc_id="SOP-M-210",
                domain=domain,
                doc_type="sop",
                plant="Osaka",
                acl_roles=roles,
                effective_date="2025-02-01",
                supersedes=None,
                entities=["PN-8801", "Plant-Osaka", "SOP-M-210"],
            ),
            """
# SOP-M-210 Cell Insertion

Insert cell PN-8801 with polarity mark facing operator left.
Press force must not exceed 80 N.
""",
        ),
        (
            "SOP-M-220-seal-test.md",
            _fm(
                doc_id="SOP-M-220",
                domain=domain,
                doc_type="sop",
                plant="Nagoya",
                acl_roles=roles,
                effective_date="2025-04-10",
                supersedes=None,
                entities=["PN-4421", "Plant-Nagoya", "SOP-M-220"],
            ),
            """
# SOP-M-220 Seal Leak Test

For assemblies using PN-4421 at Plant Nagoya, leak rate must be < 0.5 sccm at 20 kPa.
""",
        ),
        (
            "WI-M-015-calibration.md",
            _fm(
                doc_id="WI-M-015",
                domain=domain,
                doc_type="work_instruction",
                plant="Osaka",
                acl_roles=roles,
                effective_date="2025-01-20",
                supersedes=None,
                entities=["Plant-Osaka", "Tool-TW-Osaka-12"],
            ),
            """
# WI-M-015 Torque Wrench Calibration

Calibrate TW-Osaka-12 every 90 days. Out-of-tolerance tools must be quarantined.
""",
        ),
        (
            "BOM-BAT-TRAY-notes.md",
            _fm(
                doc_id="DOC-BOM-BAT-TRAY",
                domain=domain,
                doc_type="bom_note",
                plant="Osaka",
                acl_roles=roles,
                effective_date="2025-05-01",
                supersedes=None,
                entities=["BOM-BAT-TRAY", "PN-4421", "PN-8801"],
            ),
            """
# BOM Battery Tray Notes

BOM-BAT-TRAY includes fastener PN-4421 and cell PN-8801.
Torque steps reference SOP-M-105.
""",
        ),
    ]
    for filename, fm, body in docs:
        _write(domain, filename, fm, body)


def write_engineering() -> None:
    domain = "engineering"
    roles = ["engineer", "quality"]
    docs = [
        (
            "STD-E-220-connector-spec.md",
            _fm(
                doc_id="STD-E-220",
                domain=domain,
                doc_type="standard",
                plant="Global",
                acl_roles=roles,
                effective_date="2023-08-01",
                supersedes=None,
                entities=["STD-E-220", "Conn-X12"],
            ),
            """
# STD-E-220 Connector Spec

Conn-X12 pin pitch 2.0 mm. Max current 3 A per pin.
""",
        ),
        (
            "STD-E-221-connector-spec-rev.md",
            _fm(
                doc_id="STD-E-221",
                domain=domain,
                doc_type="standard",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-07-01",
                supersedes="STD-E-220",
                entities=["STD-E-221", "Conn-X12"],
            ),
            """
# STD-E-221 Connector Spec (Rev)

Conn-X12 pin pitch 2.0 mm. Max current **3.5 A** per pin.
This standard supersedes STD-E-220.
""",
        ),
        (
            "STD-E-310-thermal.md",
            _fm(
                doc_id="STD-E-310",
                domain=domain,
                doc_type="standard",
                plant="Global",
                acl_roles=roles,
                effective_date="2024-11-01",
                supersedes=None,
                entities=["STD-E-310", "PN-4421"],
            ),
            """
# STD-E-310 Thermal Design

Battery tray assemblies with PN-4421 must keep hotspot < 75°C at 1C charge.
""",
        ),
        (
            "DES-E-441-housing.md",
            _fm(
                doc_id="DES-E-441",
                domain=domain,
                doc_type="design_note",
                plant="Osaka",
                acl_roles=roles,
                effective_date="2025-03-15",
                supersedes=None,
                entities=["Housing-H7", "Plant-Osaka"],
            ),
            """
# DES-E-441 Housing H7

Housing-H7 draft angle 1.5°. Gate location on non-cosmetic face.
""",
        ),
        (
            "STD-E-050-emc.md",
            _fm(
                doc_id="STD-E-050",
                domain=domain,
                doc_type="standard",
                plant="Global",
                acl_roles=roles,
                effective_date="2022-01-01",
                supersedes=None,
                entities=["STD-E-050"],
            ),
            """
# STD-E-050 EMC Limits

Radiated emissions Class B for consumer SKUs.
""",
        ),
        (
            "STD-E-051-emc-rev.md",
            _fm(
                doc_id="STD-E-051",
                domain=domain,
                doc_type="standard",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-09-01",
                supersedes="STD-E-050",
                entities=["STD-E-051"],
            ),
            """
# STD-E-051 EMC Limits (Rev)

Radiated emissions Class B; add conducted immunity IEC 61000-4-6 Level 2.
Supersedes STD-E-050.
""",
        ),
    ]
    for filename, fm, body in docs:
        _write(domain, filename, fm, body)


def write_support() -> None:
    domain = "support"
    roles = ["support", "engineer"]
    docs = [
        (
            "KB-BAT-led-codes.md",
            _fm(
                doc_id="KB-BAT-LED",
                domain=domain,
                doc_type="kb",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-01-10",
                supersedes=None,
                entities=["Symptom-LED-3x", "Symptom-LED-5x", "KB-BAT-LED"],
            ),
            """
# Battery LED Codes

| Pattern | Meaning |
|---------|---------|
| 3× blink | Cell imbalance — follow troubleshooting tree |
| 5× blink | Charger fault |
| Solid red | Critical thermal cutout |
""",
        ),
        (
            "KB-BAT-troubleshooting-tree.md",
            _fm(
                doc_id="KB-BAT-TREE",
                domain=domain,
                doc_type="kb",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-01-10",
                supersedes=None,
                entities=["Symptom-LED-3x", "KB-BAT-TREE", "PN-8801"],
            ),
            """
# Battery Troubleshooting Tree

## LED blinks 3×
1. Power cycle device.
2. Check cell PN-8801 voltage delta < 50 mV.
3. If delta ≥ 50 mV, replace PN-8801 pack and retest.
""",
        ),
        (
            "KB-CONN-intermittent.md",
            _fm(
                doc_id="KB-CONN-INT",
                domain=domain,
                doc_type="kb",
                plant="Global",
                acl_roles=roles,
                effective_date="2024-12-01",
                supersedes=None,
                entities=["Conn-X12", "Symptom-Intermittent"],
            ),
            """
# Intermittent Conn-X12

Reseat Conn-X12; inspect for bent pins per STD-E-221.
""",
        ),
        (
            "KB-FW-update.md",
            _fm(
                doc_id="KB-FW-UPD",
                domain=domain,
                doc_type="kb",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-06-01",
                supersedes=None,
                entities=["FW-2.4.1"],
            ),
            """
# Firmware Update 2.4.1

Install FW-2.4.1 via USB recovery. Do not unplug during flash.
""",
        ),
        (
            "KB-WARRANTY-basic.md",
            _fm(
                doc_id="KB-WARRANTY",
                domain=domain,
                doc_type="kb",
                plant="Global",
                acl_roles=roles + ["support_lead"],
                effective_date="2025-01-01",
                supersedes=None,
                entities=["Policy-Warranty"],
            ),
            """
# Warranty Basics

Standard warranty 24 months from purchase. Physical damage excluded.
""",
        ),
        (
            "KB-RETURN-RMA.md",
            _fm(
                doc_id="KB-RMA",
                domain=domain,
                doc_type="kb",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-02-01",
                supersedes=None,
                entities=["TicketPattern-RMA"],
            ),
            """
# RMA Process

Open TicketPattern-RMA, capture serial, ship to regional hub within 14 days.
""",
        ),
    ]
    for filename, fm, body in docs:
        _write(domain, filename, fm, body)


def write_hr() -> None:
    domain = "hr"
    roles = ["hr", "manager", "employee"]
    docs = [
        (
            "POL-HR-pto-us.md",
            _fm(
                doc_id="POL-HR-pto-us",
                domain=domain,
                doc_type="policy",
                plant="US",
                acl_roles=roles,
                effective_date="2025-01-01",
                supersedes=None,
                entities=["POL-HR-pto-us", "Role-FT-US"],
            ),
            """
# US PTO Accrual Policy

Full-time US employees (Role-FT-US) accrue **15 days** PTO in year 1 and **20 days** from year 2.
Managers approve requests in Workday. HITL review required for automated answers.
""",
        ),
        (
            "POL-HR-travel.md",
            _fm(
                doc_id="POL-HR-travel",
                domain=domain,
                doc_type="policy",
                plant="Global",
                acl_roles=roles,
                effective_date="2024-06-01",
                supersedes=None,
                entities=["POL-HR-travel", "Role-FT-US"],
            ),
            """
# Travel Policy

Economy for flights < 6 hours. Pre-approval required above $2,500.
""",
        ),
        (
            "POL-HR-code-of-conduct.md",
            _fm(
                doc_id="POL-HR-coc",
                domain=domain,
                doc_type="policy",
                plant="Global",
                acl_roles=roles,
                effective_date="2023-01-01",
                supersedes=None,
                entities=["POL-HR-coc"],
            ),
            """
# Code of Conduct

Treat colleagues with respect. Report concerns via Ethics Hotline.
""",
        ),
        (
            "POL-HR-remote.md",
            _fm(
                doc_id="POL-HR-remote",
                domain=domain,
                doc_type="policy",
                plant="US",
                acl_roles=roles,
                effective_date="2025-03-01",
                supersedes=None,
                entities=["POL-HR-remote", "Role-FT-US"],
            ),
            """
# Remote Work (US)

Hybrid default: 3 days onsite. Exceptions require VP approval.
""",
        ),
        (
            "POL-HR-parental.md",
            _fm(
                doc_id="POL-HR-parental",
                domain=domain,
                doc_type="policy",
                plant="US",
                acl_roles=roles,
                effective_date="2024-09-01",
                supersedes=None,
                entities=["POL-HR-parental", "Role-FT-US"],
            ),
            """
# Parental Leave (US)

12 weeks paid parental leave for Role-FT-US after 12 months tenure.
""",
        ),
        (
            "POL-HR-expense.md",
            _fm(
                doc_id="POL-HR-expense",
                domain=domain,
                doc_type="policy",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-01-15",
                supersedes=None,
                entities=["POL-HR-expense"],
            ),
            """
# Expense Policy

Submit expenses within 30 days. Alcohol requires director approval.
""",
        ),
    ]
    for filename, fm, body in docs:
        _write(domain, filename, fm, body)


def write_operations() -> None:
    domain = "operations"
    roles = ["sre", "ops", "engineer"]
    docs = [
        (
            "RB-OPS-payment-service-change.md",
            _fm(
                doc_id="RB-OPS-payment-change",
                domain=domain,
                doc_type="runbook",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-05-01",
                supersedes=None,
                entities=["Svc-payment", "RB-OPS-payment-change"],
            ),
            """
# Change Window: payment-service

Approved change window: **Tue/Thu 02:00–04:00 UTC**.
Require dual approval for schema migrations.
""",
        ),
        (
            "RB-OPS-incident-sev1.md",
            _fm(
                doc_id="RB-OPS-sev1",
                domain=domain,
                doc_type="runbook",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-01-01",
                supersedes=None,
                entities=["RB-OPS-sev1", "Svc-payment"],
            ),
            """
# SEV1 Incident Runbook

Page on-call, open bridge, assign IC. Customer comms within 15 minutes.
""",
        ),
        (
            "RB-OPS-auth-service.md",
            _fm(
                doc_id="RB-OPS-auth",
                domain=domain,
                doc_type="runbook",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-02-01",
                supersedes=None,
                entities=["Svc-auth", "RB-OPS-auth"],
            ),
            """
# auth-service Runbook

If login error rate > 2%, disable new device MFA challenge experiment flag.
""",
        ),
        (
            "RB-OPS-deploy-canary.md",
            _fm(
                doc_id="RB-OPS-canary",
                domain=domain,
                doc_type="runbook",
                plant="Global",
                acl_roles=roles,
                effective_date="2024-10-01",
                supersedes=None,
                entities=["RB-OPS-canary"],
            ),
            """
# Canary Deploy

Start at 5% traffic for 20 minutes; abort on p95 > 2× baseline.
""",
        ),
        (
            "RB-OPS-backup-restore.md",
            _fm(
                doc_id="RB-OPS-backup",
                domain=domain,
                doc_type="runbook",
                plant="Global",
                acl_roles=roles,
                effective_date="2024-08-01",
                supersedes=None,
                entities=["RB-OPS-backup", "Svc-payment"],
            ),
            """
# Backup Restore

Restore payment-service Postgres from PITR; validate checksum before cutover.
""",
        ),
        (
            "RB-OPS-kafka-lag.md",
            _fm(
                doc_id="RB-OPS-kafka",
                domain=domain,
                doc_type="runbook",
                plant="Global",
                acl_roles=roles,
                effective_date="2025-04-01",
                supersedes=None,
                entities=["RB-OPS-kafka", "Svc-events"],
            ),
            """
# Kafka Consumer Lag

If Svc-events lag > 100k, scale consumers and pause non-critical producers.
""",
        ),
    ]
    for filename, fm, body in docs:
        _write(domain, filename, fm, body)


def build_entities() -> list[dict]:
    entities: list[dict] = [
        {"id": "PN-4421", "label": "Part", "name": "PN-4421", "props": {"family": "battery_tray"}},
        {"id": "PN-8801", "label": "Part", "name": "PN-8801", "props": {"family": "cell"}},
        {"id": "BOM-BAT-TRAY", "label": "BOM", "name": "Battery Tray BOM", "props": {}},
        {"id": "Plant-Osaka", "label": "Plant", "name": "Osaka Assembly", "props": {"region": "APAC"}},
        {"id": "Plant-Nagoya", "label": "Plant", "name": "Nagoya Assembly", "props": {"region": "APAC"}},
        {"id": "Line-A3", "label": "Section", "name": "Line A3", "props": {"plant": "Osaka"}},
        {"id": "Tool-TW-Osaka-12", "label": "Document", "name": "Torque Wrench TW-Osaka-12", "props": {}},
        {"id": "SOP-M-104", "label": "SOP", "name": "Torque Assembly v1", "props": {"version": 1}},
        {"id": "SOP-M-105", "label": "SOP", "name": "Torque Assembly v2", "props": {"version": 2}},
        {"id": "SOP-M-210", "label": "SOP", "name": "Cell Insertion", "props": {}},
        {"id": "SOP-M-220", "label": "SOP", "name": "Seal Leak Test", "props": {}},
        {"id": "WI-M-015", "label": "Document", "name": "Calibration WI", "props": {}},
        {"id": "DOC-BOM-BAT-TRAY", "label": "Document", "name": "BOM notes", "props": {}},
        {"id": "PLANT-OSAKA-SAFE", "label": "Document", "name": "Osaka Line Safety", "props": {}},
        {"id": "STD-E-220", "label": "Document", "name": "Connector Spec v1", "props": {}},
        {"id": "STD-E-221", "label": "Document", "name": "Connector Spec v2", "props": {}},
        {"id": "STD-E-310", "label": "Document", "name": "Thermal Design", "props": {}},
        {"id": "STD-E-050", "label": "Document", "name": "EMC Limits v1", "props": {}},
        {"id": "STD-E-051", "label": "Document", "name": "EMC Limits v2", "props": {}},
        {"id": "DES-E-441", "label": "Document", "name": "Housing H7", "props": {}},
        {"id": "Conn-X12", "label": "Part", "name": "Conn-X12", "props": {}},
        {"id": "Housing-H7", "label": "Part", "name": "Housing H7", "props": {}},
        {"id": "KB-BAT-LED", "label": "Document", "name": "LED Codes KB", "props": {}},
        {"id": "KB-BAT-TREE", "label": "Document", "name": "Troubleshooting Tree", "props": {}},
        {"id": "KB-CONN-INT", "label": "Document", "name": "Conn intermittent KB", "props": {}},
        {"id": "KB-FW-UPD", "label": "Document", "name": "FW Update KB", "props": {}},
        {"id": "KB-WARRANTY", "label": "Document", "name": "Warranty KB", "props": {}},
        {"id": "KB-RMA", "label": "Document", "name": "RMA KB", "props": {}},
        {"id": "Symptom-LED-3x", "label": "Symptom", "name": "LED blinks 3x", "props": {}},
        {"id": "Symptom-LED-5x", "label": "Symptom", "name": "LED blinks 5x", "props": {}},
        {"id": "Symptom-Intermittent", "label": "Symptom", "name": "Intermittent connection", "props": {}},
        {"id": "FW-2.4.1", "label": "Document", "name": "Firmware 2.4.1", "props": {}},
        {"id": "Policy-Warranty", "label": "Policy", "name": "Warranty Policy", "props": {}},
        {"id": "TicketPattern-RMA", "label": "TicketPattern", "name": "RMA Pattern", "props": {}},
        {"id": "POL-HR-pto-us", "label": "Policy", "name": "US PTO Accrual", "props": {"region": "US"}},
        {"id": "POL-HR-travel", "label": "Policy", "name": "Travel Policy", "props": {}},
        {"id": "POL-HR-coc", "label": "Policy", "name": "Code of Conduct", "props": {}},
        {"id": "POL-HR-remote", "label": "Policy", "name": "Remote Work US", "props": {}},
        {"id": "POL-HR-parental", "label": "Policy", "name": "Parental Leave US", "props": {}},
        {"id": "POL-HR-expense", "label": "Policy", "name": "Expense Policy", "props": {}},
        {"id": "Role-FT-US", "label": "Role", "name": "Full-time US Employee", "props": {}},
        {"id": "Role-Manager-US", "label": "Role", "name": "US Manager", "props": {}},
        {"id": "Svc-payment", "label": "Service", "name": "payment-service", "props": {}},
        {"id": "Svc-auth", "label": "Service", "name": "auth-service", "props": {}},
        {"id": "Svc-events", "label": "Service", "name": "events-service", "props": {}},
        {"id": "RB-OPS-payment-change", "label": "Document", "name": "Payment change runbook", "props": {}},
        {"id": "RB-OPS-sev1", "label": "Document", "name": "SEV1 runbook", "props": {}},
        {"id": "RB-OPS-auth", "label": "Document", "name": "Auth runbook", "props": {}},
        {"id": "RB-OPS-canary", "label": "Document", "name": "Canary runbook", "props": {}},
        {"id": "RB-OPS-backup", "label": "Document", "name": "Backup runbook", "props": {}},
        {"id": "RB-OPS-kafka", "label": "Document", "name": "Kafka lag runbook", "props": {}},
    ]
    return entities


def build_relations() -> list[dict]:
    rels: list[dict] = [
        {"src": "SOP-M-105", "rel": "SUPERSEDES", "dst": "SOP-M-104", "props": {}},
        {"src": "SOP-M-105", "rel": "APPLIES_TO", "dst": "PN-4421", "props": {"plant": "Osaka"}},
        {"src": "SOP-M-105", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "SOP-M-104", "rel": "APPLIES_TO", "dst": "PN-4421", "props": {"plant": "Osaka"}},
        {"src": "SOP-M-104", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "SOP-M-210", "rel": "APPLIES_TO", "dst": "PN-8801", "props": {}},
        {"src": "SOP-M-210", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "SOP-M-220", "rel": "APPLIES_TO", "dst": "PN-4421", "props": {"plant": "Nagoya"}},
        {"src": "SOP-M-220", "rel": "LOCATED_AT", "dst": "Plant-Nagoya", "props": {}},
        {"src": "BOM-BAT-TRAY", "rel": "PART_OF", "dst": "PN-4421", "props": {}},
        {"src": "BOM-BAT-TRAY", "rel": "PART_OF", "dst": "PN-8801", "props": {}},
        {"src": "DOC-BOM-BAT-TRAY", "rel": "REFERENCES", "dst": "BOM-BAT-TRAY", "props": {}},
        {"src": "DOC-BOM-BAT-TRAY", "rel": "REFERENCES", "dst": "SOP-M-105", "props": {}},
        {"src": "WI-M-015", "rel": "APPLIES_TO", "dst": "Tool-TW-Osaka-12", "props": {}},
        {"src": "WI-M-015", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "PLANT-OSAKA-SAFE", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "Line-A3", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "PLANT-OSAKA-SAFE", "rel": "APPLIES_TO", "dst": "Line-A3", "props": {}},
        {"src": "STD-E-221", "rel": "SUPERSEDES", "dst": "STD-E-220", "props": {}},
        {"src": "STD-E-221", "rel": "APPLIES_TO", "dst": "Conn-X12", "props": {}},
        {"src": "STD-E-220", "rel": "APPLIES_TO", "dst": "Conn-X12", "props": {}},
        {"src": "STD-E-051", "rel": "SUPERSEDES", "dst": "STD-E-050", "props": {}},
        {"src": "STD-E-310", "rel": "APPLIES_TO", "dst": "PN-4421", "props": {}},
        {"src": "DES-E-441", "rel": "APPLIES_TO", "dst": "Housing-H7", "props": {}},
        {"src": "DES-E-441", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "Symptom-LED-3x", "rel": "REQUIRES", "dst": "KB-BAT-TREE", "props": {}},
        {"src": "Symptom-LED-3x", "rel": "REFERENCES", "dst": "KB-BAT-LED", "props": {}},
        {"src": "Symptom-LED-5x", "rel": "REFERENCES", "dst": "KB-BAT-LED", "props": {}},
        {"src": "KB-BAT-TREE", "rel": "APPLIES_TO", "dst": "PN-8801", "props": {}},
        {"src": "Symptom-Intermittent", "rel": "REQUIRES", "dst": "KB-CONN-INT", "props": {}},
        {"src": "KB-CONN-INT", "rel": "REFERENCES", "dst": "STD-E-221", "props": {}},
        {"src": "KB-CONN-INT", "rel": "APPLIES_TO", "dst": "Conn-X12", "props": {}},
        {"src": "KB-FW-UPD", "rel": "REFERENCES", "dst": "FW-2.4.1", "props": {}},
        {"src": "KB-WARRANTY", "rel": "REFERENCES", "dst": "Policy-Warranty", "props": {}},
        {"src": "KB-RMA", "rel": "REFERENCES", "dst": "TicketPattern-RMA", "props": {}},
        {"src": "POL-HR-pto-us", "rel": "GOVERNS", "dst": "Role-FT-US", "props": {}},
        {"src": "POL-HR-travel", "rel": "GOVERNS", "dst": "Role-FT-US", "props": {}},
        {"src": "POL-HR-remote", "rel": "GOVERNS", "dst": "Role-FT-US", "props": {}},
        {"src": "POL-HR-parental", "rel": "GOVERNS", "dst": "Role-FT-US", "props": {}},
        {"src": "POL-HR-expense", "rel": "GOVERNS", "dst": "Role-FT-US", "props": {}},
        {"src": "POL-HR-coc", "rel": "GOVERNS", "dst": "Role-FT-US", "props": {}},
        {"src": "POL-HR-pto-us", "rel": "GOVERNS", "dst": "Role-Manager-US", "props": {"approver": True}},
        {"src": "POL-HR-remote", "rel": "GOVERNS", "dst": "Role-Manager-US", "props": {}},
        {"src": "RB-OPS-payment-change", "rel": "APPLIES_TO", "dst": "Svc-payment", "props": {}},
        {"src": "RB-OPS-sev1", "rel": "APPLIES_TO", "dst": "Svc-payment", "props": {}},
        {"src": "RB-OPS-backup", "rel": "APPLIES_TO", "dst": "Svc-payment", "props": {}},
        {"src": "RB-OPS-auth", "rel": "APPLIES_TO", "dst": "Svc-auth", "props": {}},
        {"src": "RB-OPS-kafka", "rel": "APPLIES_TO", "dst": "Svc-events", "props": {}},
        {"src": "RB-OPS-canary", "rel": "REFERENCES", "dst": "RB-OPS-payment-change", "props": {}},
        {"src": "SOP-M-105", "rel": "REFERENCES", "dst": "WI-M-015", "props": {}},
        {"src": "SOP-M-105", "rel": "PART_OF", "dst": "BOM-BAT-TRAY", "props": {}},
        {"src": "PN-4421", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "PN-8801", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "Conn-X12", "rel": "REFERENCES", "dst": "STD-E-221", "props": {}},
        {"src": "Housing-H7", "rel": "LOCATED_AT", "dst": "Plant-Osaka", "props": {}},
        {"src": "KB-BAT-LED", "rel": "REFERENCES", "dst": "Symptom-LED-3x", "props": {}},
        {"src": "KB-BAT-LED", "rel": "REFERENCES", "dst": "Symptom-LED-5x", "props": {}},
        {"src": "Policy-Warranty", "rel": "GOVERNS", "dst": "Role-FT-US", "props": {}},
        {"src": "TicketPattern-RMA", "rel": "REQUIRES", "dst": "KB-RMA", "props": {}},
        {"src": "FW-2.4.1", "rel": "REFERENCES", "dst": "KB-FW-UPD", "props": {}},
        {"src": "Svc-payment", "rel": "REFERENCES", "dst": "RB-OPS-sev1", "props": {}},
        {"src": "Svc-auth", "rel": "REFERENCES", "dst": "RB-OPS-auth", "props": {}},
        {"src": "Line-A3", "rel": "REQUIRES", "dst": "PLANT-OSAKA-SAFE", "props": {}},
        {"src": "Tool-TW-Osaka-12", "rel": "REQUIRES", "dst": "WI-M-015", "props": {}},
        {"src": "STD-E-310", "rel": "REFERENCES", "dst": "SOP-M-105", "props": {}},
        {"src": "Role-Manager-US", "rel": "PART_OF", "dst": "Role-FT-US", "props": {}},
    ]
    return rels


def write_kg() -> tuple[int, int]:
    KG.mkdir(parents=True, exist_ok=True)
    entities = build_entities()
    relations = build_relations()
    ent_path = KG / "seed_entities.jsonl"
    rel_path = KG / "seed_relations.jsonl"
    with ent_path.open("w", encoding="utf-8") as f:
        for e in entities:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with rel_path.open("w", encoding="utf-8") as f:
        for r in relations:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(entities), len(relations)


def main() -> None:
    write_manufacturing()
    write_engineering()
    write_support()
    write_hr()
    write_operations()
    n_ent, n_rel = write_kg()

    domains = ["manufacturing", "engineering", "support", "hr", "operations"]
    counts = {d: len(list((CORPUS / d).glob("*.md"))) for d in domains}
    print("Synthetic corpus written:")
    for d, n in counts.items():
        print(f"  {d}: {n} docs")
    print(f"  entities: {n_ent}")
    print(f"  relations: {n_rel}")
    if any(n < 6 for n in counts.values()):
        raise SystemExit("ERROR: need ≥ 6 docs per domain")
    if n_ent < 40 or n_rel < 60:
        raise SystemExit("ERROR: need ≥ 40 entities and ≥ 60 relations")
    print("OK")


if __name__ == "__main__":
    main()
