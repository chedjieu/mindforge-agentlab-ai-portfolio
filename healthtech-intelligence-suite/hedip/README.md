# HEDI Platform (HEDIP)

**Healthcare Effectiveness Data & Information Performance Engine** — quality-measure and payer/provider decision intelligence.

**HealthTech Intelligence Suite** sister of **[CarePath AI](../carepath-ai/README.md)** (care pathways and clinical CDS) and **[RAIP Engine](../raip/README.md)** (risk adjustment and incentive documentation). HEDIP reimplements clinical CDS as one domain; it does **not** depend on `carepath-ai` at runtime.

As-built v1 is an umbrella **Healthcare Decision Intelligence Platform** (LangGraph, GraphRAG, multi-agent reasoning): prior auth, claims denial prevention, clinical CDS, care coordination, knowledge Q&A, fraud scoring, population health, and RCM coding assist. HEDIS-style quality performance is the suite thesis and lands on the population-health, claims, RCM, and knowledge domains.

Suite landing page: [../README.md](../README.md). As-built: [AS_BUILT.md](AS_BUILT.md) · [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md).

## Quick start

From the suite root:

```powershell
cd hedip
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
uv sync --python 3.12
$env:HEDIP_MODEL = "fake"
uv run python -m app.graph
uv run python -m app.main
```

Open [http://127.0.0.1:8009](http://127.0.0.1:8009)

Local Neo4j / Postgres (from suite root): `docker compose up -d` — HEDIP maps **5436** (Postgres) and **7476 / 7689** (Neo4j).

## Quality gates

```powershell
$env:HEDIP_MODEL = "fake"
uv run python -m evals.run_all
uv run python -m security.injection_eval
```

Injection suite must pass **≥ 95%**.

## Docs

[AS_BUILT.md](AS_BUILT.md) · [docs/architecture.md](docs/architecture.md) · [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)

## Sister-project handoff

| From / to | What to share (narrative, not an API) |
|-----------|----------------------------------------|
| CarePath → HEDIP | Published care plan as context for quality / utilization review |
| HEDIP → CarePath | Gap-in-care or adherence flags that should change the pathway |
| HEDIP → RAIP | Coding and quality-gap notes for evidence-grounded documentation |

## CI gates

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR:

- `uv sync --frozen --extra dev`
- `ruff check`
- `pytest` (smoke / unit)
- `evals/run_all.py` with `*_MODEL=fake` (if present)
- injection suite ≥ 95% (if present)

### Roadmap to excellent

- HEDIS-style golden paths on synthetic members (diabetes control, medication adherence, post-discharge follow-up)
- Shared composite action for `uv` + ruff + pytest across sister packages
- Nightly LangSmith eval runs (non-fake models) on a schedule
- `uv pip audit` / dependency vulnerability gate in CI

**Not v1:** live NCQA/HEDIS certified engines, real CMS/PBM APIs, HIPAA production hardening.
