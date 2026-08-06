"""Pairwise regression — gate model/prompt deploys (position-randomized)."""

from __future__ import annotations

import os
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from langchain_core.messages import HumanMessage, SystemMessage

from app._fake_llm import is_fake_chat_model
from app.eval.judge_client import get_judge_model_name, judge_chat
from evals._common import load_jsonl, load_rubric, parse_json_blob, should_upload

GOLDEN = Path(__file__).parent / "pairwise_golden.jsonl"
EXPERIMENT = "egkp-pairwise-regression"
MIN_WIN = float(os.getenv("PAIRWISE_MIN_WIN_RATE", "0.50"))


def _fake_winner(a: str, b: str) -> str:
    # Prefer grounded answers; heavily penalize guarantee/refund fluff.
    def score(text: str) -> float:
        t = text.lower()
        s = 0.0
        if "citation" in t or "grounded" in t or "[" in text:
            s += 2
        if "clearer" in t or "steps" in t:
            s += 0.5
        if "guarantee" in t or "refund" in t or "without any sources" in t:
            s -= 5
        # Mild verbosity penalty only for very long fluff
        words = len(text.split())
        if words > 40:
            s -= 0.02 * (words - 40)
        return s

    sa, sb = score(a), score(b)
    if abs(sa - sb) < 1e-9:
        return "tie"
    return "A" if sa > sb else "B"


def judge_pair(query: str, baseline: str, candidate: str) -> str | None:
    """Return 'baseline' | 'candidate' | 'tie' | None(fail-closed)."""
    order = ["baseline", "candidate"]
    random.shuffle(order)
    mapping = {"A": order[0], "B": order[1]}
    a_text = baseline if order[0] == "baseline" else candidate
    b_text = baseline if order[1] == "baseline" else candidate

    if is_fake_chat_model(get_judge_model_name()):
        winner_ab = _fake_winner(a_text, b_text)
    else:
        raw = judge_chat(
            [
                SystemMessage(content=load_rubric("pairwise.md")),
                HumanMessage(
                    content=(
                        f"Query: {query}\n\nAnswer A:\n{a_text}\n\nAnswer B:\n{b_text}\n"
                    )
                ),
            ]
        )
        if raw is None:
            return None
        data = parse_json_blob(raw) or {}
        winner_ab = str(data.get("winner", "")).upper()
        if winner_ab not in {"A", "B", "TIE"}:
            return None
        if winner_ab == "TIE":
            winner_ab = "tie"

    if winner_ab == "tie":
        return "tie"
    return mapping[winner_ab]


def main() -> int:
    os.environ.setdefault("EGKP_MODEL", "fake")
    os.environ.setdefault("EGKP_JUDGE_MODEL", "fake")
    random.seed(int(os.getenv("PAIRWISE_SEED", "7")))

    rows = load_jsonl(GOLDEN)
    # Gate uses candidate vs baseline; also smoke worse_candidate loses.
    wins = ties = losses = 0
    for row in rows:
        # Primary gate: candidate should not lose to baseline badly
        use_worse = os.getenv("PAIRWISE_USE_WORSE", "").strip() == "1"
        cand = row["worse_candidate"] if use_worse else row["candidate"]
        result = judge_pair(row["query"], row["baseline"], cand)
        if result is None:
            print(f"FAIL-CLOSED {row['id']}")
            return 1
        if result == "candidate":
            wins += 1
            label = "WIN"
        elif result == "tie":
            ties += 1
            label = "TIE"
        else:
            losses += 1
            label = "LOSS"
        print(f"{label} {row['id']} -> {result}")

    # Tie handling: count half toward win-rate
    decided = wins + losses + ties
    win_rate = (wins + 0.5 * ties) / max(decided, 1)
    print(f"win-rate={win_rate:.2%} (wins={wins} ties={ties} losses={losses}) min={MIN_WIN}")

    if should_upload():
        try:
            from langsmith import Client

            Client().create_run(
                name=EXPERIMENT,
                inputs={"n": decided},
                outputs={"win_rate": win_rate},
                run_type="chain",
            )
        except Exception as exc:
            print(f"LangSmith upload skipped: {exc}")

    return 0 if win_rate >= MIN_WIN else 1


if __name__ == "__main__":
    raise SystemExit(main())
