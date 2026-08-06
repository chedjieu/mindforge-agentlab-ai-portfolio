# Walmart OmniKnowledge AI (WOKA)

Enterprise multi-agent knowledge intelligence platform — hybrid RAG + GraphRAG + SQL + internet + compliance — starting with Supply Chain Disruption Resolution.

## Problem

Walmart knowledge is fragmented across SOPs, contracts, inventory systems, compliance manuals, SharePoint, Confluence, Jira, ServiceNow, ERP, and external regulators. Wrong answers cost millions in inventory, fines, and disruption.

## Solution

WOKA is an **Enterprise AI Knowledge Operating System**: a LangGraph supervisor coordinates specialized agents (security, retrieval, document, SQL, internet, compliance, citation, analytics) to deliver citation-backed answers in seconds under RBAC/ABAC.

## Position vs siblings

| Project | Focus |
|---------|--------|
| **WAIP** (`../waip`) | Associate HR/payroll multi-agent + HITL |
| **WIDRA** (`../widra`) | PDF document RAG |
| **WOKA** (this) | Cross-domain knowledge OS — supply chain first |

## Quick start

```powershell
cd "c:\Users\deched\projects(ml-ai)\0.ide_vs-code_&_cursor\9.walmart\woka"
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
uv sync --python 3.12 --extra dev
uv run python scripts/generate_sample_docs.py

# Optional infra (Postgres :5434, Weaviate :8082, MinIO :9002)
$env:COMPOSE_PROJECT_NAME = "woka"
docker compose -f infra/compose/docker-compose.yml up -d
uv run python -m app.db.migrate

# Offline-safe + ingest sample docs
uv run python -m pipelines.ingest --dir data/sample_docs/
$env:WOKA_MODEL = "fake"
$env:WOKA_EMBEDDINGS = "fake"
uv run python -m app.main
```

Open [http://127.0.0.1:8006/](http://127.0.0.1:8006/) (Knowledge Console) or [http://127.0.0.1:8006/health](http://127.0.0.1:8006/health)

Golden demo query:

> Hurricane closed DCs in the Southeast. Which suppliers are affected, which products are delayed, what inventory exists within 300 miles, which contracts allow alternate sourcing, and which stores will stock out within 48 hours?

```powershell
# Smoke UC-1 (offline-safe)
$env:WOKA_MODEL = "fake"; $env:WOKA_EMBEDDINGS = "fake"
uv run python -c "from app.graph import run_uc1; r=run_uc1('Hurricane closed DCs in the Southeast. Which suppliers are affected?'); print(r['final_response'][:400]); print(r['agents_used'])"
```

## Status

**Phase 6 complete — Scale + cloud.** Concurrent batch ingest, optional Pinecone + AWS S3 modes, AgentCore/Vertex entrypoints, P95 latency smoke.

```powershell
# Batch ingest
uv run python -m pipelines.batch_ingest --dir data/sample_docs/ --workers 4

# Latency gate
uv run python -m evals.latency_smoke

# Deploy smokes
uv run python deploy/agentcore/entrypoint.py
uv run python deploy/vertex_engine/entrypoint.py
```

APIs: `POST /ingest/batch`, `POST /evaluate`, `POST /feedback`, `GET /audit`

See [AS_BUILT.md](AS_BUILT.md), [docs/architecture.md](docs/architecture.md), [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md), [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

## CI gates

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR:

- `uv sync --frozen --extra dev`
- `ruff check`
- `pytest` (smoke / unit)
- `evals/run_all.py` with `*_MODEL=fake` (if present)
- injection suite ≥ 95% (if present)

Locally: same commands from the package root.

### Roadmap to excellent

- Shared composite action for `uv` + ruff + pytest across sibling packages
- Nightly LangSmith eval runs (non-fake models) on a schedule
- `uv pip audit` / dependency vulnerability gate in CI
