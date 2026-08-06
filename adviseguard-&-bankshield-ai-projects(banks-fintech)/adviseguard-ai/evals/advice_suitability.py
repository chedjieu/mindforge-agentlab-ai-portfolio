"""Advice suitability — product matches risk tolerance."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADVISEGUARD_MODEL", "fake")
os.environ.setdefault("ADVISEGUARD_EMBEDDINGS", "fake")

from langgraph.types import Command

from app.graph import build_graph, make_initial_state


def product_for(customer_id: str, query: str) -> str:
    graph = build_graph()
    state = make_initial_state(query=query, customer_id=customer_id)
    config = {"configurable": {"thread_id": state["thread_id"]}, "recursion_limit": 60}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        graph.invoke(Command(resume={"action": "approve"}), config)
    advice = graph.get_state(config).values.get("advice_draft") or {}
    return str(advice.get("product_id") or "")


def main() -> int:
    cons = product_for("CUST-2002", "I want conservative capital preservation investment advice")
    agg = product_for("CUST-3003", "I want aggressive growth investment advice for retirement")
    print(f"conservative->{cons} aggressive->{agg}")
    ok = cons == "AG-BOND-CORE" and agg == "AG-GROWTH-EQ"
    print("ship_advice_suitability", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
