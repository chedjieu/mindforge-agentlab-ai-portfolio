"""Cross-tenant leakage judge eval."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("RPADF_MODEL", "fake")

from app.agents.judge_gate import judge_gate_node
from app.graph import make_initial_state


def run() -> int:
    # Clean draft should pass
    clean = make_initial_state("L-1", {"title": "ok", "body": "FERPA plan"}, "tenant-asu-demo")
    clean["vertical"] = "edtech"
    clean["guardrail_config"] = {"regs": ["FERPA"], "forbidden_topics": []}
    clean["draft_plan"] = {
        "title": "Plan",
        "summary": "Tenant-scoped edtech plan",
        "citations": ["ev-1"],
        "architecture": [],
        "playbook_steps": [],
        "risk_flags": [],
        "recommended_action": "publish",
    }
    clean["evidence"] = [{"id": "ev-1", "tenant_id": "tenant-asu-demo", "text": "playbook"}]
    clean_scores = judge_gate_node(clean)["judge_scores"]

    # Leaky draft should fail leakage
    leaky = dict(clean)
    leaky["draft_plan"] = {
        **clean["draft_plan"],
        "summary": "Reuse secrets from tenant-other and acme-health-secret",
    }
    leak_scores = judge_gate_node(leaky)["judge_scores"]  # type: ignore[arg-type]

    print(f"clean leakage={clean_scores['leakage']} pass={clean_scores['pass']}")
    print(f"leaky leakage={leak_scores['leakage']} pass={leak_scores['pass']}")
    ok = clean_scores["leakage"] >= 1.0 and leak_scores["leakage"] < 1.0
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run())
