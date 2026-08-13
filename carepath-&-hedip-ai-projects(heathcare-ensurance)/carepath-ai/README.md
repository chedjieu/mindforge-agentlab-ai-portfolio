# CarePath AI

AI-driven **patient care pathway** and **clinical decision support** for complex chronic-care patients.

**HealthTech Intelligence Suite** sister of **[HEDI Platform](../hedip/README.md)** (quality / HEDIS performance) and **[RAIP Engine](../raip/README.md)** (risk adjustment and evidence-grounded documentation). CarePath stays clinical-only and does **not** call HEDIP or RAIP at runtime.

LangGraph supervisor → patient data extraction → medication interaction check → plan generation → preference incorporation → safety judge → HITL-gated publish.

Dual deploy: **Bedrock AgentCore** + **Vertex AI Agent Engine**.

Suite plans: [plan-overview](../.cursor/plan-overview.md) · [plan-carepath-ai](../.cursor/plan-carepath-ai.md).

## Quick start

From the suite root:

```powershell
cd carepath-ai
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
uv sync --python 3.12
$env:CAREPATH_MODEL = "fake"
uv run python -m app.graph
uv run python -m app.main
```

Open [http://127.0.0.1:8007](http://127.0.0.1:8007)

Local Neo4j / Postgres (from suite root): `docker compose up -d` — CarePath maps **5435** (Postgres) and **7475 / 7688** (Neo4j).

## Quality gates

```powershell
$env:CAREPATH_MODEL = "fake"
uv run python -m evals.run_all
uv run python -m security.injection_eval
```

Injection suite must pass **≥ 95%**.

## Architecture (short)

See [AS_BUILT.md](AS_BUILT.md), [docs/architecture.md](docs/architecture.md), [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md).

| Layer | Tech |
|-------|------|
| Orchestration | LangGraph supervisor loop |
| RAG | Hybrid BM25 + dense + Neo4j GraphRAG |
| Memory | Procedural / episodic / semantic |
| Models | Bedrock / Vertex via gateway (`CAREPATH_MODEL`) |
| Safety | Firewall + med checker + judge + HITL + 50-attack suite |
| Infra sketch | `infra/compose/docker-compose.yml` |

## Golden demo

> Select patient **P001** (T2DM + HTN + 6 meds). Preferences: avoid injectable GLP-1. Generate treatment plan. Approve the HITL card to publish.

Downstream in the suite: the same member can be reviewed in HEDIP for quality / utilization gaps, then documented in RAIP with claim-level citations — copy the narrative, do not wire a runtime mesh.

## Cloud models (optional)

```powershell
$env:CAREPATH_MODEL = "bedrock_converse:anthropic.claude-3-5-sonnet-20241022-v2:0"
$env:CAREPATH_JUDGE_MODEL = "google_vertexai:gemini-2.5-pro"
# or
$env:CAREPATH_MODEL = "google_vertexai:gemini-2.5-pro"
```

## Deploy adapters

```powershell
uv run python deploy/agentcore/entrypoint.py
uv run python deploy/vertex_engine/entrypoint.py
```

## CI gates

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR:

- `uv sync --frozen --extra dev`
- `ruff check`
- `pytest` (smoke / unit)
- `evals/run_all.py` with `*_MODEL=fake` (if present)
- injection suite ≥ 95% (if present)

### Roadmap to excellent

- Shared composite action for `uv` + ruff + pytest across sister packages
- Nightly LangSmith eval runs (non-fake models) on a schedule
- `uv pip audit` / dependency vulnerability gate in CI
