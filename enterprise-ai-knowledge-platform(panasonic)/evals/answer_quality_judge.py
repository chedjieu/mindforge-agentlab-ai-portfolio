"""Answer quality judge — report metric with verbosity normalization."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from langchain_core.messages import HumanMessage, SystemMessage

from app._fake_llm import is_fake_chat_model
from app.eval.judge_client import get_judge_model_name, judge_chat
from evals._common import load_jsonl, load_rubric, parse_json_blob, should_upload, token_count

GOLDEN = Path(__file__).parent / "groundedness_golden.jsonl"
EXPERIMENT = "egkp-answer-quality"


def _fake_quality(answer: str, evidence: str) -> dict:
    # Prefer shorter grounded answers: base quality from overlap, then normalize.
    from evals.groundedness_judge import _fake_ground

    g = _fake_ground(answer, evidence)
    quality = 1.0 + 4.0 * g  # map to 1-5
    # Verbosity penalty baked into reporting via length_normalized_score
    return {
        "accuracy": quality,
        "completeness": quality,
        "citation": 4.0 if "[c" in answer else 2.0,
        "safety": 5.0 if "guarantee" not in answer.lower() else 1.0,
        "quality": quality,
        "feedback": "fake quality judge",
    }


def score_row(row: dict) -> dict | None:
    answer = row.get("answer") or ""
    evidence = row.get("evidence") or ""
    if is_fake_chat_model(get_judge_model_name()):
        data = _fake_quality(answer, evidence)
    else:
        raw = judge_chat(
            [
                SystemMessage(content=load_rubric("answer_quality.md")),
                HumanMessage(
                    content=(
                        f"Query: {row.get('query')}\nAnswer: {answer}\nEvidence: {evidence}"
                    )
                ),
            ]
        )
        if raw is None:
            return None
        data = parse_json_blob(raw)
        if not data or data.get("quality") is None:
            return None
    quality = float(data["quality"])
    tokens = token_count(answer)
    length_normalized = quality / math.log2(2 + tokens)
    return {**data, "quality": quality, "token_count": tokens, "length_normalized_score": length_normalized}


def main() -> int:
    os.environ.setdefault("EGKP_MODEL", "fake")
    os.environ.setdefault("EGKP_JUDGE_MODEL", "fake")

    rows = load_jsonl(GOLDEN)
    scores: list[float] = []
    norms: list[float] = []
    for row in rows:
        result = score_row(row)
        if result is None:
            print(f"FAIL-CLOSED {row['id']}")
            return 1
        scores.append(float(result["quality"]))
        norms.append(float(result["length_normalized_score"]))
        print(
            f"{row['id']} quality={result['quality']:.2f} "
            f"len_norm={result['length_normalized_score']:.3f} tokens={result['token_count']}"
        )

    avg_q = sum(scores) / max(len(scores), 1)
    avg_n = sum(norms) / max(len(norms), 1)
    print(f"avg_quality={avg_q:.2f} avg_length_normalized_score={avg_n:.3f}")
    if should_upload():
        try:
            from langsmith import Client

            Client().create_run(
                name=EXPERIMENT,
                inputs={"n": len(scores)},
                outputs={"avg_quality": avg_q, "avg_length_normalized_score": avg_n},
                run_type="chain",
            )
        except Exception as exc:
            print(f"LangSmith upload skipped: {exc}")
    # Report-only: always exit 0 unless judge failed closed
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
