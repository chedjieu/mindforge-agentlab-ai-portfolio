"""Vertical router component eval."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))
os.environ.setdefault("RPADF_MODEL", "fake")

from app.agents.vertical_router import vertical_router_node
from app.graph import make_initial_state

GOLDEN = Path(__file__).resolve().parent / "router_golden.jsonl"


def load_golden() -> list[dict]:
    if not GOLDEN.exists():
        return [
            {
                "brief": {"title": "FERPA student onboarding", "body": "Canvas SIS enrollment"},
                "expect_vertical": "edtech",
            },
            {
                "brief": {"title": "HIPAA care ops", "body": "FHIR patient encounter triage"},
                "expect_vertical": "healthcare",
            },
            {
                "brief": {"title": "GLBA account summarizer", "body": "bank SOC2 account ops"},
                "expect_vertical": "finserv",
            },
        ]
    return [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]


def run() -> int:
    rows = load_golden()
    ok = 0
    for i, row in enumerate(rows):
        state = make_initial_state(f"R-{i}", row["brief"], "tenant-test")
        out = vertical_router_node(state)
        got = out.get("vertical")
        exp = row["expect_vertical"]
        passed = got == exp
        ok += int(passed)
        print(f"[{i}] expect={exp} got={got} {'PASS' if passed else 'FAIL'}")
    rate = ok / max(1, len(rows))
    print(f"Router pass: {ok}/{len(rows)} = {rate:.0%}")
    return 0 if rate >= 0.8 else 1


if __name__ == "__main__":
    raise SystemExit(run())
