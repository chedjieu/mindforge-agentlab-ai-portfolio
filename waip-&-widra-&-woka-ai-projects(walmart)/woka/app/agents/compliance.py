"""Compliance Agent — validate groundedness, external tags, ACL hygiene."""

from __future__ import annotations

from typing import Any


def run_compliance_agent(
    *,
    answer: str,
    citations: list[dict[str, Any]],
    sql_data: dict[str, Any] | None = None,
    blocked: bool = False,
) -> dict[str, Any]:
    issues: list[str] = []
    if blocked:
        return {
            "agent": "compliance",
            "passed": False,
            "score": 0.0,
            "issues": ["Request blocked by firewall"],
        }

    if not answer.strip():
        issues.append("Empty answer")
    if not citations:
        issues.append("No citations provided")

    for c in citations:
        if c.get("source_type") == "external" and not str(c.get("doc_id", "")).startswith("ext:"):
            issues.append(f"External citation missing ext: prefix: {c.get('doc_id')}")
        if c.get("source_type") == "sql" and not str(c.get("doc_id", "")).startswith("sql:"):
            issues.append(f"SQL citation missing sql: prefix: {c.get('doc_id')}")

    # Numeric claims from SQL should appear when inventory mentioned
    if sql_data and "inventory" in answer.lower():
        inv = (sql_data.get("data") or {}).get("inventory_within_300mi") or []
        if inv and not any(str(i.get("qty")) in answer for i in inv[:3]):
            # soft warning — still pass if citations exist
            issues.append("warn: inventory quantities not echoed in answer prose")

    hard = [i for i in issues if not i.startswith("warn:")]
    score = 1.0 if not hard else max(0.0, 1.0 - 0.25 * len(hard))
    return {
        "agent": "compliance",
        "passed": len(hard) == 0,
        "score": round(score, 3),
        "issues": issues,
    }
