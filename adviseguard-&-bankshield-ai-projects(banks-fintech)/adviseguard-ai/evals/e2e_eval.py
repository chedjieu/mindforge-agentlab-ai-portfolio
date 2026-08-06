"""End-to-end advice + fraud demos."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADVISEGUARD_MODEL", "fake")
os.environ.setdefault("ADVISEGUARD_EMBEDDINGS", "fake")

from langgraph.types import Command

from app.graph import DEMO_ADVICE_QUERY, build_graph, get_alert, make_initial_state


def run(query: str, customer_id: str, alert: dict | None = None) -> dict:
    graph = build_graph()
    state = make_initial_state(query=query, customer_id=customer_id, txn_alert=alert or {})
    config = {"configurable": {"thread_id": state["thread_id"]}, "recursion_limit": 60}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    hitl = any(intr for task in snap.tasks for intr in task.interrupts)
    if hitl:
        graph.invoke(Command(resume={"action": "approve"}), config)
    final = graph.get_state(config).values
    return {
        "intent": final.get("intent"),
        "hitl": hitl,
        "published": final.get("published"),
        "risk_band": final.get("risk_band"),
        "has_response": bool(final.get("final_response")),
    }


def main() -> int:
    advice = run(DEMO_ADVICE_QUERY, "CUST-1001")
    alert = get_alert("ALT-FRAUD-001")
    fraud = run(str(alert.get("description")), str(alert.get("customer_id")), alert)
    print("advice", advice)
    print("fraud", fraud)
    ok = (
        advice["published"]
        and advice["has_response"]
        and advice["hitl"]
        and fraud["published"]
        and fraud["hitl"]
        and fraud["risk_band"] in ("high", "critical")
    )
    print("ship_e2e", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
