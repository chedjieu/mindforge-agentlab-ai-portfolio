"""Generate NDA-safe synthetic alerts, KYC profiles, corpus, and KG seeds."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate_alerts() -> dict:
    alerts = [
        {
            "alert_id": "ALT-MULE-001",
            "case_id": "CASE-MULE-001",
            "demo_gold": "mule",
            "alert_type": "wire_mule_network",
            "description": (
                "High-value outbound wire $48,500 to new beneficiary with shared device "
                "and IP reuse across three newly opened accounts — suspected mule ring."
            ),
            "customer_id": "CUST-1001",
            "customer_name": "Alex Rivera",
            "payment_rail": "wire",
            "amount": 48500,
            "beneficiary": "BEN-9001",
            "beneficiary_name": "QuickCash Disbursements LLC",
            "beneficiary_country": "US",
            "device_id": "DEV-SHARED-77",
            "ip": "203.0.113.44",
            "phone": "+1-555-0144",
            "velocity_1h": 4,
            "velocity_24h": 11,
            "avg_amount_30d": 420,
            "new_beneficiary": True,
            "night_owl": True,
            "behavior_anomaly": 0.82,
            "ml_score": 0.88,
            "fraud_types": ["wire", "mule"],
            "needs_graph": True,
            "tags": ["wire", "mule"],
        },
        {
            "alert_id": "ALT-OFAC-001",
            "case_id": "CASE-OFAC-001",
            "demo_gold": "sanctions",
            "alert_type": "sanctions_near_match",
            "description": (
                "Wire to beneficiary name near-matching OFAC SDN fixture entry "
                "'Vladimir Petroski' / ShellTrade Ltd — sanctions screening required."
            ),
            "customer_id": "CUST-2002",
            "customer_name": "Jordan Lee",
            "payment_rail": "wire",
            "amount": 125000,
            "beneficiary": "BEN-OFAC-1",
            "beneficiary_name": "Vladimir Petroski",
            "beneficiary_country": "CY",
            "device_id": "DEV-2002",
            "ip": "198.51.100.10",
            "phone": "+1-555-0202",
            "velocity_1h": 1,
            "velocity_24h": 2,
            "avg_amount_30d": 8000,
            "new_beneficiary": True,
            "ml_score": 0.79,
            "fraud_types": ["sanctions", "wire", "aml"],
            "needs_graph": True,
            "tags": ["sanctions", "ofac", "aml"],
        },
        {
            "alert_id": "ALT-ACH-001",
            "case_id": "CASE-ACH-001",
            "alert_type": "ach_velocity",
            "description": "ACH debit burst: 9 transfers in 24h totaling $62,000 vs $900 average.",
            "customer_id": "CUST-3003",
            "customer_name": "Sam Patel",
            "payment_rail": "ach",
            "amount": 9200,
            "beneficiary": "BEN-ACH-3",
            "beneficiary_name": "Payroll Overflow Inc",
            "beneficiary_country": "US",
            "velocity_1h": 3,
            "velocity_24h": 9,
            "avg_amount_30d": 900,
            "new_beneficiary": True,
            "ml_score": 0.71,
            "fraud_types": ["ach"],
            "needs_graph": True,
            "tags": ["ach"],
        },
        {
            "alert_id": "ALT-CARD-001",
            "case_id": "CASE-CARD-001",
            "alert_type": "card_cnr",
            "description": "Card-not-present spend spike at electronics merchant overseas.",
            "customer_id": "CUST-4004",
            "customer_name": "Riley Chen",
            "payment_rail": "card",
            "amount": 2400,
            "merchant": "ElectroMart RO",
            "beneficiary_country": "RO",
            "velocity_1h": 5,
            "velocity_24h": 7,
            "avg_amount_30d": 85,
            "behavior_anomaly": 0.7,
            "ml_score": 0.66,
            "fraud_types": ["card"],
            "tags": ["card"],
        },
        {
            "alert_id": "ALT-ATO-001",
            "case_id": "CASE-ATO-001",
            "alert_type": "account_takeover",
            "description": "Password reset + new device + beneficiary add within 12 minutes.",
            "customer_id": "CUST-5005",
            "customer_name": "Morgan Blake",
            "payment_rail": "wire",
            "amount": 15000,
            "device_id": "DEV-NEW-99",
            "ip": "192.0.2.55",
            "new_beneficiary": True,
            "behavior_anomaly": 0.91,
            "ml_score": 0.84,
            "fraud_types": ["ato", "wire"],
            "needs_graph": True,
            "tags": ["ato"],
        },
        {
            "alert_id": "ALT-BEC-001",
            "case_id": "CASE-BEC-001",
            "alert_type": "app_bec",
            "description": "Business email compromise: CFO impersonation requesting urgent vendor wire.",
            "customer_id": "CUST-6006",
            "customer_name": "Northwind Manufacturing AP",
            "payment_rail": "wire",
            "amount": 275000,
            "beneficiary_name": "Global Parts Settlement",
            "new_beneficiary": True,
            "ml_score": 0.77,
            "fraud_types": ["app_bec", "wire"],
            "tags": ["bec", "app"],
        },
        {
            "alert_id": "ALT-RTP-001",
            "case_id": "CASE-RTP-001",
            "alert_type": "instant_pay",
            "description": "FedNow instant payment $7,800 to first-time payee after phishing report.",
            "customer_id": "CUST-7007",
            "customer_name": "Casey Nguyen",
            "payment_rail": "fednow",
            "amount": 7800,
            "new_beneficiary": True,
            "ml_score": 0.69,
            "fraud_types": ["instant_pay"],
            "tags": ["fednow", "rtp"],
        },
        {
            "alert_id": "ALT-LOW-001",
            "case_id": "CASE-LOW-001",
            "alert_type": "false_positive_candidate",
            "description": "Recurring ACH payroll to known employer within historical norms.",
            "customer_id": "CUST-8008",
            "customer_name": "Taylor Brooks",
            "payment_rail": "ach",
            "amount": 3200,
            "velocity_1h": 1,
            "velocity_24h": 1,
            "avg_amount_30d": 3200,
            "new_beneficiary": False,
            "ml_score": 0.18,
            "behavior_anomaly": 0.05,
            "fraud_types": ["ach"],
            "tags": ["ach", "payroll"],
        },
    ]
    # Expand to ~24 with shallow variants
    base_extra = [
        ("card", "card", "Card geolocation mismatch"),
        ("ato", "internal", "Session anomaly after SIM swap"),
        ("aml", "ach", "Structuring pattern just under CTR threshold"),
        ("app_bec", "wire", "Invoice redirect scam"),
        ("instant_pay", "rtp", "RTP romance scam indicator"),
        ("mule", "ach", "Funnel account inbound then outbound ACH"),
        ("wire", "wire", "Cross-border wire layering attempt"),
        ("sanctions", "wire", "Country risk escalation review"),
    ]
    for i, (ftype, rail, desc) in enumerate(base_extra, start=1):
        alerts.append(
            {
                "alert_id": f"ALT-VAR-{i:03d}",
                "case_id": f"CASE-VAR-{i:03d}",
                "alert_type": ftype,
                "description": f"{desc} (synthetic variant {i}).",
                "customer_id": f"CUST-9{i:03d}",
                "customer_name": f"Synthetic User {i}",
                "payment_rail": rail,
                "amount": 1000 * i + 500,
                "velocity_1h": 1 + (i % 4),
                "velocity_24h": 2 + i,
                "avg_amount_30d": 200,
                "ml_score": min(0.95, 0.35 + i * 0.06),
                "fraud_types": [ftype],
                "needs_graph": ftype in ("mule", "wire", "sanctions", "aml"),
                "tags": [ftype],
            }
        )
    return {"alerts": alerts}


def generate_kyc() -> dict:
    return {
        "profiles": [
            {
                "customer_id": "CUST-1001",
                "name": "Alex Rivera",
                "kyc_status": "verified",
                "synthetic_risk": 0.55,
                "face_match": 0.71,
                "device_fingerprint": "DEV-SHARED-77",
                "account_age_days": 18,
                "findings": ["Thin-file identity", "Device shared with 2 other customers"],
            },
            {
                "customer_id": "CUST-2002",
                "name": "Jordan Lee",
                "kyc_status": "verified",
                "synthetic_risk": 0.2,
                "face_match": 0.96,
                "account_age_days": 840,
                "findings": ["Long-standing customer"],
                "ofac_hit": False,
            },
            {
                "customer_id": "CUST-3003",
                "name": "Sam Patel",
                "kyc_status": "verified",
                "synthetic_risk": 0.15,
                "face_match": 0.94,
                "account_age_days": 400,
                "findings": [],
            },
            {
                "customer_id": "CUST-5005",
                "name": "Morgan Blake",
                "kyc_status": "reverify_required",
                "synthetic_risk": 0.35,
                "face_match": 0.4,
                "account_age_days": 210,
                "findings": ["Face match drop after device change"],
            },
            {
                "customer_id": "CUST-8008",
                "name": "Taylor Brooks",
                "kyc_status": "verified",
                "synthetic_risk": 0.05,
                "face_match": 0.99,
                "account_age_days": 1200,
                "findings": [],
            },
        ]
    }


def generate_kg() -> dict:
    return {
        "nodes": [
            {"id": "CUST-1001", "label": "Customer", "name": "Alex Rivera"},
            {"id": "CUST-1002", "label": "Customer", "name": "Jamie Ortiz"},
            {"id": "CUST-1003", "label": "Customer", "name": "Chris Nguyen"},
            {"id": "DEV-SHARED-77", "label": "Device", "fingerprint": "fp-77"},
            {"id": "IP-203.0.113.44", "label": "IP", "address": "203.0.113.44"},
            {"id": "PH-555-0144", "label": "Phone", "number": "+1-555-0144"},
            {"id": "BEN-9001", "label": "Company", "name": "QuickCash Disbursements LLC"},
            {"id": "TXN-W-1001", "label": "Transaction", "amount": 48500, "rail": "wire"},
            {"id": "TXN-W-1002", "label": "Transaction", "amount": 22000, "rail": "wire"},
            {"id": "TXN-W-1003", "label": "Transaction", "amount": 17500, "rail": "ach"},
            {"id": "CUST-2002", "label": "Customer", "name": "Jordan Lee"},
            {"id": "BEN-OFAC-1", "label": "Company", "name": "ShellTrade Ltd"},
            {"id": "COUNTRY-CY", "label": "Country", "code": "CY"},
        ],
        "edges": [
            {"source": "CUST-1001", "target": "DEV-SHARED-77", "type": "OWNS"},
            {"source": "CUST-1002", "target": "DEV-SHARED-77", "type": "SHARES_DEVICE"},
            {"source": "CUST-1003", "target": "DEV-SHARED-77", "type": "SHARES_DEVICE"},
            {"source": "CUST-1001", "target": "IP-203.0.113.44", "type": "SHARES_IP"},
            {"source": "CUST-1002", "target": "IP-203.0.113.44", "type": "SHARES_IP"},
            {"source": "CUST-1001", "target": "PH-555-0144", "type": "SHARES_PHONE"},
            {"source": "CUST-1003", "target": "PH-555-0144", "type": "SHARES_PHONE"},
            {"source": "CUST-1001", "target": "TXN-W-1001", "type": "OWNS"},
            {"source": "TXN-W-1001", "target": "BEN-9001", "type": "TRANSFERRED_TO"},
            {"source": "CUST-1002", "target": "TXN-W-1002", "type": "OWNS"},
            {"source": "TXN-W-1002", "target": "BEN-9001", "type": "TRANSFERRED_TO"},
            {"source": "CUST-1003", "target": "TXN-W-1003", "type": "OWNS"},
            {"source": "TXN-W-1003", "target": "BEN-9001", "type": "SHARES_BENEFICIARY"},
            {"source": "CUST-1002", "target": "BEN-9001", "type": "SHARES_BENEFICIARY"},
            {"source": "CUST-2002", "target": "BEN-OFAC-1", "type": "TRANSFERRED_TO"},
            {"source": "BEN-OFAC-1", "target": "COUNTRY-CY", "type": "RELATED_TO"},
        ],
    }


CORPUS = {
    "aml_policy/bsa_sar_basics.md": """---
domain: aml_policy
title: BSA SAR Filing Basics
---
# Bank Secrecy Act — SAR Basics (synthetic training excerpt)

Financial institutions must file a Suspicious Activity Report (SAR) when transactions
aggregate to $5,000 or more and the institution knows, suspects, or has reason to
suspect that the transaction involves funds from illegal activity, is designed to
evade BSA requirements, or has no business or apparent lawful purpose.

Investigators must retain supporting evidence, document the decision path, and avoid
tipping off the customer. Human review is required before filing.
""",
    "aml_policy/mule_account_guidance.md": """---
domain: aml_policy
title: Mule Account Red Flags
---
# Mule Account Red Flags

Indicators include: newly opened accounts with rapid inbound/outbound flow,
shared devices or IPs across unrelated customers, common beneficiaries,
and thin-file synthetic identity signals. Escalate when graph analysis shows
fan-in/fan-out patterns across three or more accounts.
""",
    "ofac_guidance/ofac_screening.md": """---
domain: ofac_guidance
title: OFAC Screening Requirements
---
# OFAC Screening

All cross-border wires and high-risk counterparties must be screened against the
OFAC SDN list. Near matches require secondary review. True matches must be blocked
and escalated to the sanctions officer. Do not process payments to sanctioned parties.
""",
    "ofac_guidance/fixture_sdn_hits.md": """---
domain: ofac_guidance
title: Fixture SDN Entries
---
# Fixture SDN Entries (synthetic)

- Vladimir Petroski — associated with ShellTrade Ltd
- ShellTrade Ltd — Cyprus-registered shell used in demo sanctions scenarios
- Northhaven Crypto Exchange — demo wallet cluster label
""",
    "ofac_guidance/live_feed_fixture.md": """---
domain: ofac_guidance
title: Live Feed Fixture
source: live_feed_fixture
---
# Simulated Live OFAC / FinCEN Bulletin

(2026-07-01) FinCEN highlights increased mule recruitment via instant payments.
(2026-07-10) OFAC updates emphasize shell company layering through EU/Cyprus entities.
(2026-07-20) FFIEC note: retain model explainability artifacts for AML exams.
""",
    "fraud_playbooks/wire_investigation.md": """---
domain: fraud_playbooks
title: Wire Fraud Playbook
---
# Wire Fraud Investigation Playbook

1. Verify originator identity and recent authentication events.
2. Confirm beneficiary novelty and country risk.
3. Check velocity and amount vs customer history.
4. Run graph search for shared devices/IPs/phones.
5. Retrieve AML/OFAC citations.
6. Produce recommendation with evidence IDs for HITL approval.
""",
    "fraud_playbooks/ato_playbook.md": """---
domain: fraud_playbooks
title: Account Takeover Playbook
---
# ATO Playbook

Flags: credential reset, new device, beneficiary add, immediate high-value transfer.
Freeze outbound rails pending customer contact when risk band is high/critical.
""",
    "kyc_profiles/kyc_overview.md": """---
domain: kyc_profiles
title: KYC Overview
---
# KYC Overview

Synthetic identity indicators include inconsistent SSN/address history, thin credit,
and device clustering. Face-match scores below 0.6 after device change warrant reverify.
""",
    "closed_cases/case_mule_2025.md": """---
domain: closed_cases
title: Closed Mule Ring 2025-11
---
# Closed Case: Mule Ring 2025-11

Three accounts shared device DEV-SHARED-77 and IP 203.0.113.44, funneling wires to
QuickCash Disbursements LLC. SAR filed after HITL approval. Loss avoided: $88,000.
""",
    "closed_cases/case_ofac_2025.md": """---
domain: closed_cases
title: Closed Sanctions Near-Match 2025-09
---
# Closed Case: Sanctions Near-Match

Beneficiary name matched fixture SDN Vladimir Petroski. Payment blocked, SAR filed,
sanctions officer notified. Citation: OFAC Screening Requirements.
""",
    "sar_examples/sar_template.md": """---
domain: sar_examples
title: SAR Narrative Template
---
# SAR Narrative Template

Include: who/what/when/where, payment rail, amounts, counterparties, red flags,
graph relationships, prior related cases, and investigator conclusion.
""",
}


def generate_prompts() -> None:
    prompts_dir = ROOT / "data" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    write(
        prompts_dir / "recommender_latest.json",
        json.dumps(
            {
                "version": "latest",
                "system": (
                    "You are a bank fraud investigation recommender. Cite only provided "
                    "evidence IDs. Never auto-file a SAR without human approval language."
                ),
            },
            indent=2,
        ),
    )


def main() -> None:
    alerts = generate_alerts()
    write(ROOT / "data" / "alerts" / "alerts.json", json.dumps(alerts, indent=2))
    write(ROOT / "data" / "alerts" / "kyc_profiles.json", json.dumps(generate_kyc(), indent=2))
    write(ROOT / "data" / "kg" / "mule_ring.json", json.dumps(generate_kg(), indent=2))

    for rel, body in CORPUS.items():
        write(ROOT / "data" / "corpus" / rel, body)

    # episodic memory seed
    epi = [
        {
            "case_id": "CASE-MULE-HIST",
            "fraud_types": ["wire", "mule"],
            "decision": "file_sar",
            "notes": "Shared device ring confirmed",
        },
        {
            "case_id": "CASE-OFAC-HIST",
            "fraud_types": ["sanctions"],
            "decision": "block",
            "notes": "SDN near match blocked",
        },
    ]
    write(
        ROOT / "data" / "past_investigations.jsonl",
        "\n".join(json.dumps(x) for x in epi) + "\n",
    )
    generate_prompts()
    print(f"Generated {len(alerts['alerts'])} alerts, corpus, KG, KYC, prompts.")


if __name__ == "__main__":
    main()
