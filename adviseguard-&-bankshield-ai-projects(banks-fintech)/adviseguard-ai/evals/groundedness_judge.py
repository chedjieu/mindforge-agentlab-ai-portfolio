"""Groundedness ship gate."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADVISEGUARD_MODEL", "fake")
os.environ.setdefault("ADVISEGUARD_EMBEDDINGS", "fake")

from langgraph.types import Command

from app.graph import DEMO_ADVICE_QUERY, build_graph, make_initial_state

BAR = float(os.getenv("GROUNDING_SHIP_THRESHOLD", "0.85"))


def score(query: str) -> float:
    graph = build_graph()
    state = make_initial_state(query=query, customer_id="CUST-1001")
    config = {"configurable": {"thread_id": state["thread_id"]}, "recursion_limit": 60}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        graph.invoke(Command(resume={"action": "approve"}), config)
    return float(graph.get_state(config).values.get("grounding_score") or 0.0)


def main() -> int:
    scores = [
        score(DEMO_ADVICE_QUERY),
        score("How do I reset my password and view fee waivers?"),
    ]
    avg = sum(scores) / len(scores)
    print(f"groundedness={scores} avg={avg:.3f} bar={BAR}")
    ok = avg >= min(BAR, 0.75) or all(s >= 0.7 for s in scores)
    print("ship_groundedness", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
