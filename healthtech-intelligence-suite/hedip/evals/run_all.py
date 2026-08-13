"""HEDIP golden evals."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("HEDIP_MODEL", "fake")
os.environ.setdefault("HEDIP_EMBEDDINGS", "fake")
os.environ.setdefault("HEDIP_JUDGE_MODEL", "fake")

from langgraph.types import Command

from app.graph import build_graph_with_backends, make_initial_state
from app.state import Domain

CASES: list[tuple[Domain, str, str | None]] = [
    ("prior_auth", "PA-MRI-001", "need_info"),
    ("prior_auth", "PA-BIO-002", "deny"),
    ("prior_auth", "PA-ONC-003", "approve"),
    ("claims", "CLM-001", "fix_first"),
    ("clinical_cds", "CDS-P001", "plan_ready"),
    ("knowledge", "KNOW-001", "answered"),
    ("care_coord", "CARE-001", "care_plan"),
    ("fraud", "FRD-001", "investigate"),
    ("pop_health", "POP-001", "risk_stratified"),
    ("rcm", "RCM-001", "coding_draft"),
]


def run_case(domain: Domain, case_id: str) -> dict:
    graph = build_graph_with_backends()
    tid = str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    state = make_initial_state(
        thread_id=tid,
        domain=domain,
        case_id=case_id,
        query=f"Run {domain} case {case_id}",
    )
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    snap = graph.get_state(config)
    if any(intr for task in snap.tasks for intr in task.interrupts):
        graph.invoke(Command(resume={"action": "approve"}), config)
        snap = graph.get_state(config)
    return dict(snap.values)


def main() -> int:
    print("HEDIP evals (fake)")
    failures: list[str] = []
    for domain, case_id, expected in CASES:
        values = run_case(domain, case_id)
        decision = (values.get("recommendation") or {}).get("decision")
        published = values.get("published")
        ok = published and (expected is None or decision == expected)
        print(f"  {'PASS' if ok else 'FAIL'} {domain}/{case_id} decision={decision} published={published}")
        if not ok:
            failures.append(f"{domain}/{case_id}: got {decision}, published={published}")
        if domain == "clinical_cds":
            renal = (values.get("recommendation") or {}).get("renal_adjustments") or []
            if not renal:
                failures.append("CDS missing metformin renal adjustment")
                print("  FAIL CDS renal")
    if failures:
        print("FAILED:")
        for f in failures:
            print(" -", f)
        return 1
    print("All domain goldens passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
