"""E2E RoboForge eval."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("RFAI_MODEL", "fake")

from langgraph.types import Command

from app.graph import SAMPLE_CLIENT, SAMPLE_PACK, build_graph, make_initial_state


def run() -> int:
    graph = build_graph()
    config = {"configurable": {"thread_id": f"e2e-{uuid.uuid4().hex[:8]}"}}
    state = make_initial_state("RF-E2E", SAMPLE_PACK, SAMPLE_CLIENT)
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(getattr(t, "interrupts", None) for t in (snap.tasks or ())):
        graph.invoke(Command(resume={"action": "approve"}), config)
    final = graph.get_state(config).values
    ok = (
        final.get("domain") == "agentic"
        and final.get("published") is True
        and bool(final.get("delivery_pack_id"))
        and bool(final.get("judge_scores"))
    )
    print(
        f"domain={final.get('domain')} published={final.get('published')} "
        f"pack={final.get('delivery_pack_id')}"
    )
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
