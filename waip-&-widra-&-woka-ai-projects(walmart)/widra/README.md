# Walmart Intelligent Document Retrieval Assistant (WIDRA)

Enterprise RAG platform for 5,000+ critical PDF documents — semantic search, role-based access, and cited conversational answers.

## Problem

Walmart employees spend hours manually searching a fragmented corpus of 5,000+ PDFs (policies, SOPs, financial reports, compliance docs). Content mixes plain text, tables, and figures. There is no unified, secure way to ask natural-language questions and get accurate, source-cited answers.

## Solution

WIDRA ingests PDFs through a multi-stage pipeline, stores chunks + embeddings + metadata in a scalable tiered stack, and serves a conversational query interface guarded by dynamic RBAC. Five specialized agents orchestrate ingestion, retrieval, answer generation, authorization, and observability.

## Architecture (short)

| Layer | Tech |
|-------|------|
| Orchestration | LangGraph supervisor + 5 agents |
| Ingestion | PDF parse (text/tables/images), semantic chunking, metadata extraction |
| Storage | S3 (source PDFs), PostgreSQL (metadata + ACL), Pinecone/Weaviate (vectors) |
| Retrieval | Hybrid dense + BM25 + metadata filters + rerank |
| Answer | LLM grounded on retrieved chunks; numeric/table facts via deterministic extractors |
| Auth | RBAC/ABAC filters applied at retrieval time (not post-hoc) |
| UI | FastAPI BFF + conversational console with source citations |
| Observability | Structured logs, traces, ingestion/query metrics, eval harness |
| Models | Bedrock / Vertex via gateway; `fake` for offline dev |

See [docs/architecture.md](docs/architecture.md), [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md), [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

## Project layout (planned)

```
widra/
├── app/              # Query service, agents, API
├── pipelines/        # Ingestion batch + incremental jobs
├── infra/            # Docker Compose (Postgres, Weaviate, MinIO)
├── data/             # Sample PDFs, eval Q&A sets
├── evals/            # Retrieval + answer quality gates
├── security/         # RBAC tests, injection suite
├── deploy/           # Cloud deploy adapters
└── docs/             # Design + runbooks
```

## Status

**Phase 2 — Ingestion pipeline complete.** PDF parse → chunk → embed → index with local fallback when Docker services are down.

## Quick start

```powershell
cd "c:\Users\deched\projects(ml-ai)\0.ide_vs-code_&_cursor\9.walmart\widra"
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
uv sync --python 3.12 --extra dev
uv run python scripts/generate_sample_pdfs.py

# Optional: Start infra (Postgres :5433, Weaviate :8081, MinIO :9000)
docker compose -f infra/compose/docker-compose.yml up -d
uv run python -m app.db.migrate

# Ingest sample PDFs (works offline via data/local_store/)
uv run python -m pipelines.ingest --dir data/sample_pdfs/

# Run API
uv run python -m app.main
```

Open [http://127.0.0.1:8005/health](http://127.0.0.1:8005/health)

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

Ingest via API:

```powershell
curl -X POST http://127.0.0.1:8005/ingest -H "Content-Type: application/json" -d "{}"
```

Stub query:

```powershell
curl -X POST http://127.0.0.1:8005/query `
  -H "Content-Type: application/json" `
  -d '{"query":"What is the return policy for damaged goods?"}'
```

## Quality gates (later phases)

## Relationship to WAIP

| | **WAIP** (`../waip`) | **WIDRA** (this project) |
|--|----------------------|--------------------------|
| Focus | Associate HR/payroll/leave multi-agent assistant | Enterprise PDF document retrieval |
| Corpus | Structured playbooks + KG + policy chunks | 5,000+ unstructured PDFs |
| Agents | Domain workers (HR, Payroll, …) | Pipeline agents (Ingest, Retrieve, Answer, Auth, Observe) |
| Shared patterns | LangGraph, hybrid RAG, ABAC, citation judges, fake LLM dev mode | Reuses same patterns, different domain |
