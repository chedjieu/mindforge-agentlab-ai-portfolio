"""Vertex AI Agent Engine-style local smoke entrypoint."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HEDIP_MODEL", "fake")

from langgraph.types import Command

from app.graph import build_graph_with_backends, make_initial_state


def run_smoke() -> dict:
    graph = build_graph_with_backends()
    tid = str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    state = make_initial_state(
        thread_id=tid, domain="claims", case_id="CLM-001", query="Claims denial risk"
    )
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        graph.invoke(Command(resume={"action": "approve"}), config)
        snap = graph.get_state(config)
    return {
        "runtime": "vertex_engine",
        "published": snap.values.get("published"),
        "decision": (snap.values.get("recommendation") or {}).get("decision"),
    }


if __name__ == "__main__":
    result = run_smoke()
    print(result)
    raise SystemExit(0 if result.get("published") else 1)
