"""Compliance judge offline eval."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("RPADF_MODEL", "fake")

from app.agents.compliance_mapper import compliance_mapper_node
from app.agents.judge_gate import judge_gate_node
from app.graph import make_initial_state


def run() -> int:
    cases = [
        ("edtech", "tenant-asu-demo"),
        ("healthcare", "tenant-careco"),
        ("finserv", "tenant-northbank"),
    ]
    ok = 0
    for vertical, tenant in cases:
        state = make_initial_state("C-1", {"title": vertical, "body": vertical}, tenant)
        state["vertical"] = vertical  # type: ignore[typeddict-item]
        state["policy_pack_id"] = f"{vertical}-v1"
        mapped = compliance_mapper_node(state)
        state.update(mapped)
        state["draft_plan"] = {
            "title": f"{vertical} plan",
            "summary": f"Compliant {vertical} plan with citations",
            "citations": ["ev-1"],
            "architecture": ["LangGraph"],
            "playbook_steps": ["policy", "reuse", "audit"],
            "risk_flags": [],
            "recommended_action": "publish",
        }
        state["evidence"] = [{"id": "ev-1", "text": "playbook", "tenant_id": tenant}]
        judged = judge_gate_node(state)
        scores = judged["judge_scores"]
        passed = scores["compliance"] >= 0.9 and scores["leakage"] >= 1.0
        ok += int(passed)
        print(f"{vertical}: compliance={scores['compliance']} leakage={scores['leakage']} {'PASS' if passed else 'FAIL'}")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(run())
