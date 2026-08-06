"""End-to-end demo alert suite."""

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


def run(alert_id: str) -> dict:
    graph = build_graph()
    state = make_initial_state(alert=get_alert(alert_id))
    config = {"configurable": {"thread_id": state["thread_id"]}}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    hitl = any(intr for task in snap.tasks for intr in task.interrupts)
    if hitl:
        graph.invoke(Command(resume={"action": "approve"}), config)
    final = graph.get_state(config).values
    return {
        "alert_id": alert_id,
        "hitl": hitl,
        "published": bool(final.get("published")),
        "risk_band": final.get("risk_band"),
        "has_sar": bool(final.get("sar_draft")),
        "evidence_n": len(final.get("evidence") or []),
    }


def main() -> int:
    results = [
        run("ALT-MULE-001"),
        run("ALT-OFAC-001"),
        run("ALT-CARD-001"),
        run("ALT-LOW-001"),
    ]
    for r in results:
        print(r)
    high = [r for r in results if r["alert_id"] in ("ALT-MULE-001", "ALT-OFAC-001")]
    ok = all(r["hitl"] and r["published"] and r["has_sar"] and r["evidence_n"] > 0 for r in high)
    print("ship_e2e", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
