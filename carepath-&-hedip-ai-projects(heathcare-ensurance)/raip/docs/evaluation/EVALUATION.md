# Evaluation

Run (Git Bash on this Windows checkout — do not use `uv run`):

```bash
export RAIP_MODEL=fake
export RAIP_HITL=evaluate
bash scripts/with-python.sh -m evals.run_all
bash scripts/with-python.sh -m security.injection_eval
```

Results are written to:

- `evals/reports/latest.json`
- `security/reports/injection.json`

**Measured (2026-08-13, `RAIP_MODEL=fake`):**

- Pytest: **20 passed**
- Golden evals: **29/29 (100%)** — see `evals/reports/latest.json`
- Injection: **50/50 (100%)** — see `security/reports/injection.json`

These are local fake-model results, not a clinical validation study.

## Suites

| Suite | What | Gate |
|-------|------|------|
| Golden authoring / retrieval / grounding | Deterministic fake-model cases | ≥ 80% of cases (expect ~all with fake) |
| Injection | 50 attacks | ≥ 95% detection |
| Pytest | Unit, integration, e2e, tenant isolation | All pass |

## Metrics (implemented)

Retrieval: hit presence, provenance (page, checksum, tier), tenant leak check.  
Generation: metformin grounded, DrugZ absent, EVIDENCE GAP on CRISPR.  
Safety: critical unsupported claim ⇒ BLOCKED even if weighted score is high.  
System: cost estimate field, model version on provenance.

LLM-as-judge is **secondary** (`get_judge_model`) and cannot override a critical gate.

## Thresholds (configurable via `RAIP_*`)

Grounding ≥ 95% (policy target for promotion). Citation ≥ 95%. Unsupported rate ≤ 1% on material claims without an explicit gap. Injection ≥ 95%. Critical safety failures = 0 for promote.

The fake CI suite validates *mechanism*, not a production clinical study.
