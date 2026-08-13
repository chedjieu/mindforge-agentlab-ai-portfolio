"""Vertex AI Agent Engine-style entrypoint for CarePath AI."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("CAREPATH_MODEL", "fake")
os.environ.setdefault("CAREPATH_MEMORY", os.getenv("CAREPATH_MEMORY", "memory"))

from langgraph.types import Command

from app.graph import build_graph_with_backends, make_initial_state


def run_smoke(patient_id: str = "P001") -> dict:
    graph = build_graph_with_backends()
    tid = str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    state = make_initial_state(thread_id=tid, patient_id=patient_id)
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        graph.invoke(Command(resume={"action": "approve"}), config)
        snap = graph.get_state(config)
    return {
        "thread_id": tid,
        "published": snap.values.get("published"),
        "safety_score": snap.values.get("safety_score"),
        "runtime": "vertex_engine",
    }


if __name__ == "__main__":
    result = run_smoke()
    print(result)
    if not result.get("published"):
        raise SystemExit(1)
