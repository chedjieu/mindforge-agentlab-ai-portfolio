"""Risk-band consistency — gold high-risk demos must not score low."""

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


def risk_for(alert_id: str) -> tuple[float, str]:
    graph = build_graph()
    state = make_initial_state(alert=get_alert(alert_id))
    config = {"configurable": {"thread_id": state["thread_id"]}}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        graph.invoke(Command(resume={"action": "approve"}), config)
    final = graph.get_state(config).values
    return float(final.get("risk_score") or 0.0), str(final.get("risk_band") or "low")


def main() -> int:
    mule_score, mule_band = risk_for("ALT-MULE-001")
    ofac_score, ofac_band = risk_for("ALT-OFAC-001")
    low_score, low_band = risk_for("ALT-LOW-001")
    print(
        f"mule={mule_score}/{mule_band} ofac={ofac_score}/{ofac_band} "
        f"low={low_score}/{low_band}"
    )
    ok = (
        mule_band in ("high", "critical", "medium")
        and ofac_band in ("high", "critical")
        and low_score < mule_score
    )
    print("ship_risk_consistency", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
