# WIDRA Implementation Plan

Phased delivery for the Walmart Intelligent Document Retrieval Assistant. Each phase ends with a demoable milestone and explicit quality gates.

---

## Phase 0 — Design lock ✅

**Deliverables:** System design, architecture, locked decisions, project scaffold.

**Exit criteria:** Stakeholder sign-off on scope, agent model, storage choices, and eval gates.

---

## Phase 1 — Foundation (Week 1–2)

**Goal:** Runnable local stack with fake models and sample corpus.

| Task | Output |
|------|--------|
| Scaffold Python package (`widra`), pyproject.toml, uv | `uv sync` works |
| Docker Compose: Postgres, Weaviate, MinIO | `infra/compose/docker-compose.yml` |
| PostgreSQL schema: documents, chunks, ACL, audit | Migration scripts |
| `.env.example` + fake model gateway | Offline dev path |
| FastAPI health + stub `/query` endpoint | Port 8005 |
| 10 sample PDFs in `data/sample_pdfs/` | Seed corpus |

**Demo:** `curl /health` → 200; compose stack up.

---

## Phase 2 — Ingestion pipeline (Week 2–4) ✅

**Goal:** End-to-end PDF → chunks → vectors → metadata.

| Task | Output |
|------|--------|
| S3/MinIO upload adapter | `pipelines/upload.py` |
| PDF parser (Unstructured or Docling) | Text + table extraction |
| Semantic + table-aware chunker | `pipelines/chunker.py` |
| Batch embedder with checkpointing | `pipelines/embed.py` |
| Index writer (Weaviate + Postgres) | `pipelines/index.py` |
| Ingestion Agent (LangGraph) | `app/agents/ingestion.py` |
| CLI: `uv run python -m pipelines.ingest --dir data/sample_pdfs/` | Batch ingest command |
| Ingest job tracking + error reporting | `ingest_jobs` table |

**Quality gate:** 50 PDFs ingested with < 2% parse failures; tables preserved in chunks.

**Demo:** Ingest 10 PDFs → query Postgres for chunk count → vectors in Weaviate.

---

## Phase 3 — Retrieval + Auth (Week 4–5)

**Goal:** Hybrid search with RBAC enforced before retrieval.

| Task | Output |
|------|--------|
| ACL policy model + seed roles | `data/acl/seed_policies.yaml` |
| Auth Agent: resolve user → filter scope | `app/agents/auth.py` |
| Hybrid retriever (BM25 + dense) | `app/rag/retriever.py` |
| Cross-encoder reranker (or LLM rerank fallback) | `app/rag/rerank.py` |
| Retrieval Agent | `app/agents/retrieval.py` |
| RBAC leak test suite | `security/rbac_eval.py` — **100% pass required** |

**Quality gate:** recall@5 ≥ 0.80 on 30-question golden set; zero RBAC leaks.

**Demo:** Two users with different roles → same query → different chunk sets.

---

## Phase 4 — Answer generation + UI (Week 5–6)

**Goal:** Cited conversational answers with table fact support.

| Task | Output |
|------|--------|
| Answer Agent with citation assembly | `app/agents/answer.py` |
| Table fact extractor (deterministic) | `app/rag/table_facts.py` |
| LangGraph supervisor wiring | `app/graph.py` |
| Streaming SSE `/query` endpoint | FastAPI |
| Web console (HTML/HTMX or minimal React) | Source cards with page links |
| Groundedness + citation eval harness | `evals/answer_eval.py` |

**Quality gate:** 100% citation coverage on golden set; table queries match source cells.

**Demo:** Golden query → streamed answer with 2+ source citations.

---

## Phase 5 — Observability + hardening (Week 6–7)

**Goal:** Production-ready observability and security gates.

| Task | Output |
|------|--------|
| Observability Agent + structured logging | `app/agents/observability.py` |
| OpenTelemetry / LangSmith integration | Trace every query |
| Injection eval suite (50 attacks) | `security/injection_eval.py` — **≥ 95%** |
| Audit log (append-only) | `audit_log` table + JSONL |
| Load test script (100 concurrent queries) | P95 < 3s on sample corpus |
| Runbooks | `docs/RUNBOOK.md` |

**Quality gate:** All eval suites pass; injection ≥ 95%.

---

## Phase 6 — Scale ingest + cloud prep (Week 7–8)

**Goal:** Ready for 5,000+ document batch and cloud deploy.

| Task | Output |
|------|--------|
| Batch ingestion at scale (checkpointing, parallelism) | Process 500 docs/hour target |
| Pinecone adapter (prod vector store) | Env-switchable backend |
| S3 prod adapter | IAM-scoped upload |
| Deploy entrypoints (Bedrock AgentCore + Vertex) | `deploy/` |
| Blue/green re-index procedure | Documented in runbook |
| Full eval on expanded golden set (100 Q) | Report in `evals/results/` |

**Demo:** Ingest 200+ PDFs overnight; morning queries work with citations.

---

## Milestone summary

| Phase | Milestone | Key metric |
|-------|-----------|------------|
| 1 | Local stack runs | Health check pass |
| 2 | PDFs ingested | 50 docs, < 2% fail |
| 3 | RBAC retrieval works | 0% leak, recall@5 ≥ 0.80 |
| 4 | Cited answers in UI | 100% citation coverage |
| 5 | Security + observability | Injection ≥ 95% |
| 6 | Scale-ready | 200+ doc batch ingest |

---

## Team & effort estimate

| Role | Allocation | Focus |
|------|------------|-------|
| Backend / ML engineer | 1 FTE | Pipeline, RAG, agents |
| Full-stack engineer | 0.5 FTE | UI, API, auth mock |
| DevOps | 0.25 FTE | Compose, cloud deploy |
| QA / eval | 0.25 FTE | Golden sets, RBAC tests |

**Total:** ~8 weeks to production-ready v1 with 5k doc scale path.

---

## Dependencies

- Sample PDF corpus from Walmart (or synthetic equivalents for dev)  
- ACL policy definitions from security / compliance team  
- Cloud accounts: AWS (Bedrock, S3, Pinecone) or GCP (Vertex, GCS)  
- LangSmith or equivalent for trace evals (optional in dev)  

---

## Open questions (resolve in Phase 1)

1. **PDF parser:** Unstructured vs Docling — benchmark on 20 representative Walmart PDFs.  
2. **Vector DB prod:** Pinecone vs Weaviate Cloud — decide based on metadata filter performance.  
3. **Table strategy:** Keep tables as markdown chunks vs separate structured store for numeric queries.  
4. **SSO timeline:** Mock auth sufficient for v1 demo; Entra ID in v2.  
