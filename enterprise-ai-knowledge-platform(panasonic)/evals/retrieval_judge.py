"""Retrieval judge — ship gate for retrieval config changes."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from langchain_core.messages import HumanMessage, SystemMessage

from app._fake_llm import is_fake_chat_model
from app.eval.judge_client import get_judge_model_name, judge_chat
from app.tools.hybrid_search import hybrid_search
from evals._common import load_jsonl, load_rubric, parse_json_blob, should_upload

GOLDEN = Path(__file__).parent / "retrieval_golden.jsonl"
EXPERIMENT = "egkp-retrieval-judge"
PASS_THRESHOLD = float(os.getenv("RETRIEVAL_SHIP_THRESHOLD", "0.70"))


def _fake_score(query: str, role: str, domain: str, terms: list[str], chunks: list[dict]) -> dict:
    if not chunks or chunks[0].get("chunk_id") == "EMPTY":
        return {"relevance": 0.0, "coverage": 0.0, "acl_ok": True, "score": 0.0, "feedback": "empty"}
    blob = " ".join((c.get("text") or "") + " " + str(c.get("doc_id") or "") for c in chunks).lower()
    hits = sum(1 for t in terms if t.lower() in blob)
    coverage = hits / max(len(terms), 1)
    relevance = 1.0 if chunks else 0.0
    acl_ok = True
    for c in chunks:
        acl = (c.get("metadata") or {}).get("acl_roles") or []
        if isinstance(acl, str):
            acl = []
        if acl and role not in acl:
            acl_ok = False
    score = 0.45 * relevance + 0.45 * coverage + 0.10 * (1.0 if acl_ok else 0.0)
    return {
        "relevance": relevance,
        "coverage": coverage,
        "acl_ok": acl_ok,
        "score": score,
        "feedback": "fake retrieval judge",
    }


def score_row(row: dict) -> dict:
    query = row["query"]
    role = row.get("role") or "engineer"
    domain = row.get("domain")
    terms = row.get("must_include_terms") or []
    try:
        chunks = hybrid_search(query=query, domain=domain, role=role, k=5)
    except Exception:
        chunks = []

    if is_fake_chat_model(get_judge_model_name()):
        return _fake_score(query, role, domain or "", terms, chunks)

    rubric = load_rubric("retrieval.md")
    raw = judge_chat(
        [
            SystemMessage(content=rubric),
            HumanMessage(
                content=(
                    f"Query: {query}\nRole: {role}\nDomain: {domain}\n"
                    f"Chunks: {chunks[:5]}\nRequired terms: {terms}"
                )
            ),
        ]
    )
    if raw is None:
        return {"score": None, "feedback": "judge failure", "fail_closed": True}
    data = parse_json_blob(raw) or {}
    score = data.get("score")
    if score is None:
        return {"score": None, "feedback": "parse failure", "fail_closed": True}
    return {**data, "score": float(score)}


def main() -> int:
    os.environ.setdefault("EGKP_MODEL", "fake")
    os.environ.setdefault("EGKP_EMBEDDINGS", "fake")
    os.environ.setdefault("EGKP_JUDGE_MODEL", "fake")

    rows = load_jsonl(GOLDEN)
    passed = 0
    judged = 0
    fail_closed = False
    for row in rows:
        result = score_row(row)
        score = result.get("score")
        if score is None:
            fail_closed = True
            print(f"FAIL-CLOSED {row['id']}: {result.get('feedback')}")
            continue
        judged += 1
        ok = float(score) >= PASS_THRESHOLD
        passed += int(ok)
        print(f"{'PASS' if ok else 'FAIL'} {row['id']} score={float(score):.2f}")

    if fail_closed or judged == 0:
        print("SHIP GATE FAIL (fail-closed)")
        return 1
    rate = passed / judged
    print(f"pass-rate={rate:.2%} ({passed}/{judged}) threshold={PASS_THRESHOLD}")
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
    return 0 if rate >= PASS_THRESHOLD else 1


if __name__ == "__main__":
    raise SystemExit(main())
