"""Citation / evidence ID resolution coverage."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("BANKSHIELD_MODEL", "fake")
os.environ.setdefault("BANKSHIELD_EMBEDDINGS", "fake")

from langgraph.types import Command

from app.graph import build_graph, get_alert, make_initial_state


def coverage(alert_id: str) -> float:
    graph = build_graph()
    state = make_initial_state(alert=get_alert(alert_id))
    config = {"configurable": {"thread_id": state["thread_id"]}}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        graph.invoke(Command(resume={"action": "approve"}), config)
    final = graph.get_state(config).values
    rec = final.get("recommendation") or {}
    eids = rec.get("evidence_ids") or []
    real = {e.get("id") for e in (final.get("evidence") or [])}
    if not eids:
        return 0.0
    return len([x for x in eids if x in real]) / len(eids)


def main() -> int:
    scores = [coverage("ALT-MULE-001"), coverage("ALT-OFAC-001")]
    avg = sum(scores) / len(scores)
    print(f"citation_coverage={scores} avg={avg:.3f}")
    ok = avg >= 0.9
    print("ship_citation_coverage", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
