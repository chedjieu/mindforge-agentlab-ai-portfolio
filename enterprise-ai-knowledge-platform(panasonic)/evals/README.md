# EGKP evaluation suite

Judge infrastructure for production decisions. Bias mitigations: cross-provider judge (`EGKP_JUDGE_MODEL`), length-normalized quality, randomized pairwise order, fail-closed on judge errors.

## Gate types

| Script | Gate | Decision |
|--------|------|----------|
| `retrieval_judge.py` | **Ship retrieval** | Pass-rate ≥ `RETRIEVAL_SHIP_THRESHOLD` (default 0.70) |
| `groundedness_judge.py` | **Ship / publish** | Labels match score vs `GROUNDING_SHIP_THRESHOLD` (default 0.85); **fail closed** if judge returns `None` |
| `pairwise_regression.py` | **Gate deploy** | Candidate win-rate ≥ `PAIRWISE_MIN_WIN_RATE` (default 0.50, ties count 0.5) |
| `e2e_eval.py` | **Ship e2e** | Domain + citations + grounding + HITL expectation; pass-rate ≥ 0.80 |
| `answer_quality_judge.py` | **Report only** | Avg quality + `length_normalized_score`; does not block unless judge fails closed |

## Quick start

```powershell
$env:EGKP_MODEL='fake'
$env:EGKP_EMBEDDINGS='fake'
$env:EGKP_JUDGE_MODEL='fake'
uv run python evals/generate_goldens.py
uv run python evals/run_all.py
```

Full e2e (≥25 rows):

```powershell
$env:EGKP_E2E_LIMIT='26'
uv run python evals/e2e_eval.py
```

Set `LANGSMITH_API_KEY` to upload experiment markers (`egkp-*-judge` / `egkp-e2e-eval` / `egkp-pairwise-regression`).

## Rubrics

See [`rubrics/`](rubrics/) — `groundedness.md`, `answer_quality.md`, `retrieval.md`, `pairwise.md`.
