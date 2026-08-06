"""Eval runner — judges, injection, UC-1 quality, latency, LangSmith flag."""

from __future__ import annotations

import json
import os
from typing import Any

os.environ.setdefault("WOKA_MODEL", "fake")
os.environ.setdefault("WOKA_EMBEDDINGS", "fake")

from evals.injection_suite import run_injection_suite
from evals.judges import evaluate_answer
from evals.latency_smoke import run_latency_smoke

GOLDEN_QUERY = (
    "Hurricane closed DCs in the Southeast. Which suppliers are affected, "
    "which products are delayed, what inventory exists within 300 miles, "
    "which contracts allow alternate sourcing, and which stores will stock out within 48 hours?"
)


def uc1_quality() -> dict[str, Any]:
    from app.graph import run_uc1
    from app.llm import reset_llm_cache

    reset_llm_cache()
    state = run_uc1(GOLDEN_QUERY, role="analyst", department="Supply Chain", region="SE")
    answer = str(state.get("final_response") or state.get("answer") or "")
    eval_result = evaluate_answer(
        query=GOLDEN_QUERY,
        answer=answer,
        citations=list(state.get("citations") or []),
        sql=state.get("sql"),
        blocked=bool(state.get("blocked")),
    )
    return {
        "name": "uc1_quality",
        "pass": bool(eval_result.get("pass")) and bool(state.get("citations")),
        "eval": eval_result,
        "agents": state.get("agents_used"),
        "citation_count": len(state.get("citations") or []),
        "answer_preview": answer[:240],
    }


def langsmith_status() -> dict[str, Any]:
    key = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY") or ""
    tracing = (os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2") or "").lower() in {
        "1",
        "true",
        "yes",
    }
    return {
        "name": "langsmith",
        "configured": bool(key),
        "tracing_env": tracing,
        "project": os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT") or "woka",
        "pass": True,
    }


def rbac_smoke() -> dict[str, Any]:
    try:
        from security.rbac_eval import run_rbac_eval

        result = run_rbac_eval()
        return {
            "name": "rbac_eval",
            "pass": bool(result.get("pass")),
            "details": result,
        }
    except Exception as exc:  # noqa: BLE001
        return {"name": "rbac_eval", "pass": False, "error": str(exc)}


def run_all() -> dict[str, Any]:
    results = [
        run_injection_suite(),
        uc1_quality(),
        rbac_smoke(),
        run_latency_smoke(iterations=3),
        langsmith_status(),
    ]
    required = [r for r in results if r.get("name") != "langsmith"]
    return {
        "pass": all(bool(r.get("pass")) for r in required),
        "phase": 6,
        "results": results,
    }


if __name__ == "__main__":
    out = run_all()
    print(json.dumps(out, indent=2, default=str))
    raise SystemExit(0 if out["pass"] else 1)
