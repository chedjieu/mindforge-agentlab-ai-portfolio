"""Generate NDA-safe synthetic customers, alerts, corpus, and KG seeds."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


CORPUS = {
    "advice_playbooks/retirement_moderate.md": """---
domain: advice_playbooks
title: Moderate Retirement Advice Playbook
---
# Moderate Retirement Playbook

For moderate risk tolerance, prefer a diversified 60/40 equity-bond mix.
Rebalance annually. Document goals and avoid promising guaranteed returns.
""",
    "advice_playbooks/aggressive_growth.md": """---
domain: advice_playbooks
title: Aggressive Growth Playbook
---
# Aggressive Growth

Higher equity allocation may suit long horizons. Escalate for HITL when recommending
aggressive sleeves. Disclose volatility and lack of return guarantees.
""",
    "products/balanced_60.md": """---
domain: products
title: AG-BALANCED-60
---
# Balanced 60/40 Portfolio (AG-BALANCED-60)

Diversified ETF sleeve targeting moderate risk. Suitable for retirement goals with
10+ year horizon. Not FDIC insured; investment risk applies.
""",
    "products/bond_core.md": """---
domain: products
title: AG-BOND-CORE
---
# Core Bond Fund (AG-BOND-CORE)

Capital-preservation oriented bond fund for conservative investors.
""",
    "products/growth_eq.md": """---
domain: products
title: AG-GROWTH-EQ
---
# Growth Equity Sleeve (AG-GROWTH-EQ)

Higher volatility equity sleeve for aggressive risk tolerance.
""",
    "regulations/suitability.md": """---
domain: regulations
title: Suitability and Disclosure
---
# Suitability

Recommendations must align with customer risk tolerance and goals.
Do not use guaranteed-return language. High-stakes advice requires human review.
""",
    "fraud_patterns/velocity_wire.md": """---
domain: fraud_patterns
title: Wire Velocity Fraud Pattern
---
# Wire Velocity Pattern

Multiple high-value wires to new beneficiaries within one hour, especially with
shared devices across accounts, indicate mule or ATO risk. Escalate high/critical bands.
""",
    "fraud_patterns/device_reuse.md": """---
domain: fraud_patterns
title: Shared Device Fraud Pattern
---
# Shared Device Pattern

Device reuse across unrelated customers plus outbound transfers is a strong fraud signal.
""",
    "support_kb/fees.md": """---
domain: support_kb
title: Account Fees FAQ
---
# Fees FAQ

Monthly maintenance fees may be waived with qualifying balances.
Statements are available in online banking under Documents.
""",
    "support_kb/password_reset.md": """---
domain: support_kb
title: Password Reset
---
# Password Reset

Customers can reset passwords via the secure banking portal. After a reset,
review recent devices and beneficiaries for account-takeover risk.
""",
    "market_fixture/live_feed.md": """---
domain: market_fixture
title: Live Market and Fraud Trend Feed
source: live_feed
---
# Simulated Live Feed

(2026-07-01) Equity volatility elevated; rebalancing guidance in demand.
(2026-07-12) Instant-payment mule recruitment trends rising.
(2026-07-20) Bond yields steady; conservative sleeves remain popular.
""",
}


def main() -> None:
    customers = {
        "customers": [
            {
                "customer_id": "CUST-1001",
                "name": "Alex Rivera",
                "risk_tolerance": "moderate",
                "goals": ["retirement", "emergency_fund"],
                "holdings": ["AG-BALANCED-60"],
                "account_id": "ACC-1001",
            },
            {
                "customer_id": "CUST-2002",
                "name": "Jordan Lee",
                "risk_tolerance": "conservative",
                "goals": ["capital_preservation"],
                "holdings": ["AG-BOND-CORE"],
                "account_id": "ACC-2002",
            },
            {
                "customer_id": "CUST-3003",
                "name": "Sam Patel",
                "risk_tolerance": "aggressive",
                "goals": ["growth", "retirement"],
                "holdings": ["AG-GROWTH-EQ"],
                "account_id": "ACC-3003",
            },
        ]
    }
    alerts = {
        "alerts": [
            {
                "alert_id": "ALT-FRAUD-001",
                "demo_gold": "fraud",
                "customer_id": "CUST-1001",
                "description": "Suspicious high-value wire to new beneficiary with shared device",
                "payment_rail": "wire",
                "amount": 42000,
                "velocity_1h": 4,
                "avg_amount_30d": 500,
                "new_beneficiary": True,
                "behavior_anomaly": 0.8,
                "device_id": "DEV-SHARED-77",
                "beneficiary_country": "US",
            },
            {
                "alert_id": "ALT-LOW-001",
                "customer_id": "CUST-2002",
                "description": "Recurring ACH payroll within historical norms",
                "payment_rail": "ach",
                "amount": 3200,
                "velocity_1h": 1,
                "avg_amount_30d": 3200,
                "new_beneficiary": False,
                "behavior_anomaly": 0.05,
            },
        ]
    }
    # Expand shallow alerts
    for i in range(1, 16):
        alerts["alerts"].append(
            {
                "alert_id": f"ALT-VAR-{i:03d}",
                "customer_id": f"CUST-9{i:03d}",
                "description": f"Synthetic txn variant {i} for queue coverage",
                "payment_rail": "card" if i % 2 else "ach",
                "amount": 800 + i * 120,
                "velocity_1h": 1 + (i % 3),
                "avg_amount_30d": 200,
                "new_beneficiary": i % 4 == 0,
                "behavior_anomaly": min(0.9, 0.1 * i),
            }
        )

    kg = {
        "nodes": [
            {"id": "CUST-1001", "label": "Customer", "name": "Alex Rivera"},
            {"id": "ACC-1001", "label": "Account"},
            {"id": "PROD-BAL", "label": "Product", "code": "AG-BALANCED-60"},
            {"id": "GOAL-RET", "label": "Goal", "name": "retirement"},
            {"id": "DEV-SHARED-77", "label": "Device"},
            {"id": "CUST-1002", "label": "Customer", "name": "Jamie Ortiz"},
            {"id": "TXN-W-1", "label": "Transaction", "amount": 42000},
            {"id": "MERCH-QC", "label": "Merchant", "name": "QuickCash LLC"},
            {"id": "FP-VELOCITY", "label": "FraudPattern", "name": "wire_velocity"},
        ],
        "edges": [
            {"source": "CUST-1001", "target": "ACC-1001", "type": "OWNS"},
            {"source": "CUST-1001", "target": "GOAL-RET", "type": "OWNS"},
            {"source": "PROD-BAL", "target": "GOAL-RET", "type": "SUITABLE_FOR"},
            {"source": "CUST-1001", "target": "PROD-BAL", "type": "SIMILAR_TO"},
            {"source": "CUST-1001", "target": "DEV-SHARED-77", "type": "OWNS"},
            {"source": "CUST-1002", "target": "DEV-SHARED-77", "type": "SHARES_DEVICE"},
            {"source": "CUST-1001", "target": "TXN-W-1", "type": "OWNS"},
            {"source": "TXN-W-1", "target": "MERCH-QC", "type": "TRANSFERRED_TO"},
            {"source": "TXN-W-1", "target": "FP-VELOCITY", "type": "MATCHES_PATTERN"},
        ],
    }

    write(ROOT / "data" / "customers" / "customers.json", json.dumps(customers, indent=2))
    write(ROOT / "data" / "alerts" / "alerts.json", json.dumps(alerts, indent=2))
    write(ROOT / "data" / "kg" / "fin_graph.json", json.dumps(kg, indent=2))
    for rel, body in CORPUS.items():
        write(ROOT / "data" / "corpus" / rel, body)
    write(
        ROOT / "data" / "past_interactions.jsonl",
        json.dumps(
            {
                "customer_id": "CUST-1001",
                "intent": "advice",
                "decision": "recommend_balanced",
            }
        )
        + "\n",
    )
    write(
        ROOT / "data" / "prompts" / "advisor_latest.json",
        json.dumps(
            {
                "version": "latest",
                "system": (
                    "You are AdviseGuard. Provide suitable, disclosed advice; never promise "
                    "guaranteed returns; escalate high-stakes and high fraud risk to HITL."
                ),
            },
            indent=2,
        ),
    )
    print(
        f"Generated {len(customers['customers'])} customers, "
        f"{len(alerts['alerts'])} alerts, corpus, KG, prompts."
    )


if __name__ == "__main__":
    main()
