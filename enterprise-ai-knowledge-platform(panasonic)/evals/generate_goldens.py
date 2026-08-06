"""Generate golden eval JSONL files (≥25 e2e rows + retrieval/groundedness sets)."""

from __future__ import annotations

import json
from pathlib import Path

EVALS = Path(__file__).resolve().parent


def _w(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {path.name}: {len(rows)}")


def main() -> None:
    golden = [
        {"id": "Q-E01", "query": "What torque specification applies to part PN-4421 on the Osaka assembly line?", "role": "engineer", "expected_domain": "manufacturing", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E02", "query": "What is PTO accrual for full-time US employees?", "role": "employee", "expected_domain": "hr", "expect_hitl": True, "expect_citation": True},
        {"id": "Q-E03", "query": "LED blinks 3 times on power-up — what is the procedure?", "role": "support", "expected_domain": "support", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E04", "query": "Which SOP superseded SOP-M-104?", "role": "engineer", "expected_domain": "manufacturing", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E05", "query": "What is the change window for payment-service?", "role": "sre", "expected_domain": "operations", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E06", "query": "What is Conn-X12 max current per STD-E-221?", "role": "engineer", "expected_domain": "engineering", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E07", "query": "Remote work policy for US full-time employees?", "role": "employee", "expected_domain": "hr", "expect_hitl": True, "expect_citation": True},
        {"id": "Q-E08", "query": "How do I RMA a device?", "role": "support", "expected_domain": "support", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E09", "query": "SEV1 incident first steps?", "role": "sre", "expected_domain": "operations", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E10", "query": "Which EMC standard supersedes STD-E-050?", "role": "engineer", "expected_domain": "engineering", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E11", "query": "Seal leak test requirement for PN-4421 at Nagoya?", "role": "quality", "expected_domain": "manufacturing", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E12", "query": "Parental leave for Role-FT-US?", "role": "hr", "expected_domain": "hr", "expect_hitl": True, "expect_citation": True},
        {"id": "Q-E13", "query": "Firmware update steps for FW-2.4.1?", "role": "support", "expected_domain": "support", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E14", "query": "Kafka consumer lag runbook threshold?", "role": "sre", "expected_domain": "operations", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E15", "query": "Thermal hotspot limit for PN-4421 assemblies?", "role": "engineer", "expected_domain": "engineering", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E16", "query": "Torque wrench calibration interval for TW-Osaka-12?", "role": "manufacturing", "expected_domain": "manufacturing", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E17", "query": "Travel policy flight class under 6 hours?", "role": "employee", "expected_domain": "hr", "expect_hitl": True, "expect_citation": True},
        {"id": "Q-E18", "query": "Intermittent Conn-X12 troubleshooting?", "role": "support", "expected_domain": "support", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E19", "query": "auth-service high login error rate runbook?", "role": "sre", "expected_domain": "operations", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E20", "query": "Housing-H7 draft angle from DES-E-441?", "role": "engineer", "expected_domain": "engineering", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E21", "query": "Cell insertion force limit for PN-8801?", "role": "manufacturing", "expected_domain": "manufacturing", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E22", "query": "Expense submission deadline?", "role": "employee", "expected_domain": "hr", "expect_hitl": True, "expect_citation": True},
        {"id": "Q-E23", "query": "Warranty duration basics?", "role": "support", "expected_domain": "support", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E24", "query": "Canary deploy abort condition?", "role": "sre", "expected_domain": "operations", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E25", "query": "Does SOP-M-105 apply to PN-4421 at Plant Osaka?", "role": "engineer", "expected_domain": "manufacturing", "expect_hitl": False, "expect_citation": True},
        {"id": "Q-E26", "query": "Code of conduct reporting channel?", "role": "employee", "expected_domain": "hr", "expect_hitl": True, "expect_citation": True},
    ]
    _w(EVALS / "golden.jsonl", golden)

    retrieval = []
    for row in golden[:12]:
        retrieval.append(
            {
                "id": row["id"],
                "query": row["query"],
                "role": row["role"],
                "domain": row["expected_domain"],
                "must_include_terms": _terms(row["query"]),
            }
        )
    _w(EVALS / "retrieval_golden.jsonl", retrieval)

    groundedness = [
        {
            "id": "G-01",
            "query": "PN-4421 torque Osaka",
            "answer": "Per SOP-M-105, apply 12 N·m ± 0.5 for PN-4421 at Plant Osaka. [c1]",
            "evidence": "Apply 12 N·m ± 0.5 using calibrated torque wrench TW-Osaka-12. PN-4421 Plant Osaka SOP-M-105.",
            "citations": [{"citation_id": "c1", "doc_id": "SOP-M-105", "quote": "12 N·m ± 0.5"}],
            "expect_pass": True,
        },
        {
            "id": "G-02",
            "query": "PN-4421 torque",
            "answer": "Torque is 99 N·m guaranteed by tomorrow SLA.",
            "evidence": "Apply 12 N·m ± 0.5 for PN-4421.",
            "citations": [],
            "expect_pass": False,
        },
        {
            "id": "G-03",
            "query": "PTO accrual",
            "answer": "Full-time US employees accrue 15 days PTO in year 1. [c1]",
            "evidence": "Full-time US employees accrue 15 days PTO in year 1 and 20 days from year 2.",
            "citations": [{"citation_id": "c1", "doc_id": "POL-HR-pto-us", "quote": "15 days PTO in year 1"}],
            "expect_pass": True,
        },
        {
            "id": "G-04",
            "query": "payment-service window",
            "answer": "Change window is Tue/Thu 02:00–04:00 UTC. [c1]",
            "evidence": "Approved change window: Tue/Thu 02:00–04:00 UTC.",
            "citations": [{"citation_id": "c1", "doc_id": "RB-OPS-payment-change", "quote": "Tue/Thu 02:00–04:00 UTC"}],
            "expect_pass": True,
        },
        {
            "id": "G-05",
            "query": "LED 3x",
            "answer": "Replace the motherboard immediately without checking voltage.",
            "evidence": "Power cycle device. Check cell PN-8801 voltage delta < 50 mV.",
            "citations": [],
            "expect_pass": False,
        },
        {
            "id": "G-06",
            "query": "STD-E-221 current",
            "answer": "Conn-X12 max current is 3.5 A per pin per STD-E-221. [c1]",
            "evidence": "Conn-X12 pin pitch 2.0 mm. Max current 3.5 A per pin. Supersedes STD-E-220.",
            "citations": [{"citation_id": "c1", "doc_id": "STD-E-221", "quote": "3.5 A per pin"}],
            "expect_pass": True,
        },
        {
            "id": "G-07",
            "query": "supersede SOP-M-104",
            "answer": "SOP-M-105 supersedes SOP-M-104. [c1]",
            "evidence": "This SOP supersedes SOP-M-104. SOP-M-105 Torque Assembly v2.",
            "citations": [{"citation_id": "c1", "doc_id": "SOP-M-105", "quote": "supersedes SOP-M-104"}],
            "expect_pass": True,
        },
        {
            "id": "G-08",
            "query": "warranty",
            "answer": "Lifetime is lifetime with free upgrades forever.",
            "evidence": "Standard warranty 24 months from purchase.",
            "citations": [],
            "expect_pass": False,
        },
    ]
    _w(EVALS / "groundedness_golden.jsonl", groundedness)

    pairwise = []
    for row in golden[:8]:
        pairwise.append(
            {
                "id": row["id"],
                "query": row["query"],
                "baseline": f"Grounded answer for: {row['query']} with citations.",
                "candidate": f"Grounded answer for: {row['query']} with citations and clearer steps.",
                "worse_candidate": "I guarantee refunds tomorrow without any sources or evidence.",
            }
        )
    _w(EVALS / "pairwise_golden.jsonl", pairwise)


def _terms(query: str) -> list[str]:
    import re

    toks = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-]+", query)
    skip = {"what", "is", "the", "for", "and", "how", "do", "a", "an", "to", "of", "on"}
    out = [t for t in toks if t.lower() not in skip][:4]
    return out


if __name__ == "__main__":
    main()
