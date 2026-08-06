"""End-to-end engagement eval (fake model)."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("RPADF_MODEL", "fake")

from app.graph import SAMPLE_BRIEF, SAMPLE_TENANT, build_graph, make_initial_state


def run() -> int:
    graph = build_graph()
    state = make_initial_state("ENG-E2E", SAMPLE_BRIEF, SAMPLE_TENANT)
    config = {"configurable": {"thread_id": f"e2e-{uuid.uuid4().hex[:8]}"}}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    final = graph.get_state(config).values
    vertical_ok = final.get("vertical") == "edtech"
    has_scores = bool(final.get("judge_scores"))
    done = final.get("published") or final.get("approval") in ("pending", "auto", "approved")
    # EdTech may auto-publish or pause; either is fine if vertical + scores present
    print(f"vertical={final.get('vertical')} published={final.get('published')} approval={final.get('approval')}")
    print(f"steps={len(final.get('step_log') or [])} scores={final.get('judge_scores')}")
    ok = vertical_ok and has_scores and done
    # If HITL pending, still OK for e2e skeleton
    if final.get("approval") == "pending" and has_scores and vertical_ok:
        ok = True
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
