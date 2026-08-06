"""Latency smoke — UC-1 P95 target < 5s on sample/fake stack."""

from __future__ import annotations

import json
import os
import statistics
import time
from typing import Any

os.environ.setdefault("WOKA_MODEL", "fake")
os.environ.setdefault("WOKA_EMBEDDINGS", "fake")

GOLDEN = (
    "Hurricane closed DCs in the Southeast. Which suppliers are affected "
    "and what inventory exists within 300 miles?"
)


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def run_latency_smoke(*, iterations: int = 5, p95_budget_sec: float = 5.0) -> dict[str, Any]:
    from app.graph import run_uc1
    from app.llm import reset_llm_cache

    reset_llm_cache()
    # Warmup
    run_uc1(GOLDEN)
    times: list[float] = []
    for _ in range(max(1, iterations)):
        t0 = time.perf_counter()
        state = run_uc1(GOLDEN)
        elapsed = time.perf_counter() - t0
        times.append(elapsed)
        if not (state.get("final_response") or state.get("answer")):
            return {
                "name": "latency_smoke",
                "pass": False,
                "error": "empty answer",
                "times_sec": times,
            }

    p50 = _percentile(times, 50)
    p95 = _percentile(times, 95)
    return {
        "name": "latency_smoke",
        "pass": p95 < p95_budget_sec,
        "iterations": len(times),
        "p50_sec": round(p50, 4),
        "p95_sec": round(p95, 4),
        "mean_sec": round(statistics.mean(times), 4),
        "max_sec": round(max(times), 4),
        "budget_p95_sec": p95_budget_sec,
        "times_sec": [round(t, 4) for t in times],
    }


if __name__ == "__main__":
    out = run_latency_smoke()
    print(json.dumps(out, indent=2))
    raise SystemExit(0 if out["pass"] else 1)
