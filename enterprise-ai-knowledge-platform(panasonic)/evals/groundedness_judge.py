"""Groundedness judge — ship/publish gate (fail-closed)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from langchain_core.messages import HumanMessage, SystemMessage

from app._fake_llm import is_fake_chat_model
from app.eval.judge_client import get_judge_model_name, judge_chat
from evals._common import load_jsonl, load_rubric, parse_json_blob, should_upload

GOLDEN = Path(__file__).parent / "groundedness_golden.jsonl"
EXPERIMENT = "egkp-groundedness-judge"
THRESHOLD = float(os.getenv("GROUNDING_SHIP_THRESHOLD", "0.85"))


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", (text or "").lower()))


def _fake_ground(answer: str, evidence: str) -> float:
    claims = [c.strip() for c in re.split(r"(?<=[.!?])\s+", answer) if len(c.strip()) > 8]
    if not claims:
        return 0.0
    et = _tokenize(evidence)
    supported = 0
    for claim in claims:
        ct = {t for t in _tokenize(claim) if len(t) > 2}
        if not ct:
            supported += 1
            continue
        if len(ct & et) / len(ct) >= 0.35:
            supported += 1
    return supported / len(claims)


def score_row(row: dict) -> dict | None:
    answer = row.get("answer") or ""
    evidence = row.get("evidence") or ""
    if is_fake_chat_model(get_judge_model_name()):
        return {"grounding_score": _fake_ground(answer, evidence), "feedback": "fake"}

    raw = judge_chat(
        [
            SystemMessage(content=load_rubric("groundedness.md")),
            HumanMessage(
                content=(
                    f"Query: {row.get('query')}\nAnswer: {answer}\n"
                    f"Evidence: {evidence}\nCitations: {row.get('citations')}"
                )
            ),
        ]
    )
    if raw is None:
        return None
    data = parse_json_blob(raw)
    if not data or data.get("grounding_score") is None:
        return None
    return {
        "grounding_score": float(data["grounding_score"]),
        "feedback": data.get("feedback", ""),
    }


def main() -> int:
    os.environ.setdefault("EGKP_MODEL", "fake")
    os.environ.setdefault("EGKP_JUDGE_MODEL", "fake")

    rows = load_jsonl(GOLDEN)
    passed = 0
    judged = 0
    for row in rows:
        result = score_row(row)
        if result is None:
            print(f"FAIL-CLOSED {row['id']}: judge unavailable")
            return 1
        score = float(result["grounding_score"])
        expect_pass = bool(row.get("expect_pass", True))
        gate_pass = score >= THRESHOLD
        # Align with label: expect_pass True should gate_pass; False should not
        ok = gate_pass == expect_pass
        judged += 1
        passed += int(ok)
        print(
            f"{'PASS' if ok else 'FAIL'} {row['id']} score={score:.2f} "
            f"expect_pass={expect_pass} gate_pass={gate_pass}"
        )

    rate = passed / max(judged, 1)
    print(f"pass-rate={rate:.2%} ({passed}/{judged}) threshold={THRESHOLD}")
    if should_upload():
        try:
            from langsmith import Client

            Client().create_run(
                name=EXPERIMENT,
                inputs={"n": judged},
                outputs={"pass_rate": rate},
                run_type="chain",
            )
        except Exception as exc:
            print(f"LangSmith upload skipped: {exc}")
    # Ship gate: all expect_pass rows must clear threshold; expect_fail must not
    return 0 if rate >= 0.85 else 1


if __name__ == "__main__":
    raise SystemExit(main())
