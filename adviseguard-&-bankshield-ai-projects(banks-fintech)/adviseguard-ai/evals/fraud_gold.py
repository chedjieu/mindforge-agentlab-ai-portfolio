"""Fraud gold alert must score high/critical."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADVISEGUARD_MODEL", "fake")
os.environ.setdefault("ADVISEGUARD_EMBEDDINGS", "fake")

from langgraph.types import Command

from app.graph import build_graph, get_alert, make_initial_state


def main() -> int:
    alert = get_alert("ALT-FRAUD-001")
    graph = build_graph()
    state = make_initial_state(
        query=str(alert.get("description")),
        customer_id=str(alert.get("customer_id")),
        txn_alert=alert,
    )
    config = {"configurable": {"thread_id": state["thread_id"]}, "recursion_limit": 60}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        graph.invoke(Command(resume={"action": "approve"}), config)
    final = graph.get_state(config).values
    band = final.get("risk_band")
    finding = final.get("fraud_finding") or {}
    print(f"band={band} finding={finding.get('txn_risk_score')}")
    ok = band in ("high", "critical") and float(finding.get("txn_risk_score") or 0) >= 0.65
    print("ship_fraud_gold", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
