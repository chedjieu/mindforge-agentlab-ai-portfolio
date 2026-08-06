"""End-to-end eval — full graph vs golden domain/citation/HITL/grounding."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from langgraph.types import Command

from app.graph import build_graph, make_initial_state
from evals._common import load_jsonl, should_upload

GOLDEN = Path(__file__).parent / "golden.jsonl"
EXPERIMENT = "egkp-e2e-eval"
THRESHOLD = float(os.getenv("GROUNDING_SHIP_THRESHOLD", "0.85"))


def _has_pending_interrupt(graph, config: dict) -> bool:
    snap = graph.get_state(config)
    return any(intr for task in snap.tasks for intr in task.interrupts)


def run_one(row: dict) -> dict:
    graph = build_graph()
    thread_id = f"e2e-{row['id']}-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}
    state = make_initial_state(
        thread_id=thread_id,
        query=row["query"],
        user_id=f"eval-{row['id']}",
        role=row.get("role") or "engineer",
    )
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass

    hit_interrupt = _has_pending_interrupt(graph, config)
    # Auto-approve so eval completes; HITL expectation checked via interrupt/pending.
    while _has_pending_interrupt(graph, config):
        graph.invoke(Command(resume={"action": "approve", "edited_body": None}), config)

    final = graph.get_state(config).values
    citations = final.get("citations") or []
    return {
        "domain": final.get("domain"),
        "grounding_score": final.get("grounding_score"),
        "has_citation": bool(citations) and citations[0].get("chunk_id") != "EMPTY",
        "hit_interrupt": hit_interrupt,
        "approval": final.get("approval"),
        "published": final.get("published"),
        "recommended_action": (final.get("draft_answer") or {}).get("recommended_action"),
    }


def main() -> int:
    os.environ.setdefault("EGKP_MODEL", "fake")
    os.environ.setdefault("EGKP_EMBEDDINGS", "fake")
    os.environ.setdefault("EGKP_JUDGE_MODEL", "fake")

    rows = load_jsonl(GOLDEN)
    limit = os.getenv("EGKP_E2E_LIMIT", "").strip()
    if limit.isdigit():
        rows = rows[: int(limit)]

    if len(rows) < 25 and not limit:
        print(f"ERROR: golden set has {len(rows)} rows; need ≥ 25")
        return 1

    passed = 0
    for row in rows:
        out = run_one(row)
        domain_ok = out["domain"] == row["expected_domain"]
        cite_ok = bool(out["has_citation"]) if row.get("expect_citation", True) else True
        g = out["grounding_score"]
        ground_ok = g is not None and float(g) >= THRESHOLD
        # HITL: sensitive paths should have interrupted OR recommended hitl before auto-approve
        expect_hitl = bool(row.get("expect_hitl"))
        hitl_ok = (out["hit_interrupt"] is True) if expect_hitl else True
        # Non-HITL rows should generally publish after auto path
        publish_ok = True if expect_hitl else bool(out["published"])

        ok = domain_ok and cite_ok and ground_ok and hitl_ok and publish_ok
        passed += int(ok)
        print(
            f"{'PASS' if ok else 'FAIL'} {row['id']} "
            f"domain={out['domain']} cite={out['has_citation']} "
            f"ground={out['grounding_score']} hitl={out['hit_interrupt']} "
            f"published={out['published']}"
        )
        if not ok:
            print(
                f"  expected domain={row['expected_domain']} hitl={expect_hitl} "
                f"checks domain_ok={domain_ok} cite_ok={cite_ok} "
                f"ground_ok={ground_ok} hitl_ok={hitl_ok} publish_ok={publish_ok}"
            )

    rate = passed / max(len(rows), 1)
    print(f"pass-rate={rate:.2%} ({passed}/{len(rows)})")
    if should_upload():
        try:
            from langsmith import Client

            Client().create_run(
                name=EXPERIMENT,
                inputs={"n": len(rows)},
                outputs={"pass_rate": rate},
                run_type="chain",
            )
        except Exception as exc:
            print(f"LangSmith upload skipped: {exc}")
    return 0 if rate >= 0.80 else 1


if __name__ == "__main__":
    raise SystemExit(main())
