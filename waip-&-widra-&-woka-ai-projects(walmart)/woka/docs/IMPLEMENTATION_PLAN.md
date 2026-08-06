# WOKA Implementation Plan

## Phase 0 — Design lock ✅

AS_BUILT, SYSTEM_DESIGN, ARCHITECTURE, IMPLEMENTATION_PLAN, `.env`.

## Phase 1 — Foundation ✅ (this delivery)

Package, Compose, schema + SQL seeds, fake LLM, FastAPI `/health` `/chat` stubs, sample docs.

**Exit:** health 200; fake smoke.

## Phase 2 — Ingestion + classification ✅

Classify → parse → chunk → embed → index; Document Agent; CLI ingest.

**Exit:** sample docs indexed with ACL metadata.

## Phase 3 — Security + hybrid retrieval ✅

Security Agent, hybrid retriever, GraphRAG, RBAC leak 0%, recall-oriented golden search.

**Exit:** `/search` returns ACL-scoped chunks + graph facts; `python -m security.rbac_eval` passes 100%.

## Phase 4 — Multi-agent UC-1 ✅

Orchestrator + SQL + internet + compliance + citation + streaming UI.

**Exit:** golden hurricane query fully answered with citations; `/chat` + `/chat/stream` + console at `/`.

## Phase 5 — Eval + hardening ✅

LLM-as-judge, injection ≥95%, LangSmith hooks, `/audit` `/evaluate` `/feedback`.

**Exit:** `uv run python -m evals.run_all` passes; injection block ≥95%; UC-1 judges pass.

## Phase 6 — Scale + cloud ✅

Batch ingest, Pinecone/S3 adapters, AgentCore + Vertex entrypoints, P95 < 5s.

**Exit:** `uv run python -m evals.latency_smoke` passes; deploy entrypoint smokes; `/ingest/batch` works.

## Milestone summary

| Phase | Milestone | Metric |
|-------|-----------|--------|
| 1 | Local stack | Health ok |
| 2 | Docs ingested | Sample corpus indexed |
| 3 | Secure retrieval | 0% leak, recall@5 ≥ 0.80 |
| 4 | UC-1 demo | Cited multi-agent answer |
| 5 | Quality gates | ≥95% groundedness/citation |
| 6 | Cloud-ready | Deploy smoke |
