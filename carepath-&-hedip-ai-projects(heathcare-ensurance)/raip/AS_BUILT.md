# As-Built — ReguMed Authoring Intelligence Platform (RAIP)

**Package:** `regumed-authoring-ai` v0.1.0  
**UI:** Review console `http://127.0.0.1:8011`  
**Date:** 2026-08-13

This file describes **what is implemented**. It does not claim production certification, live cloud deploys, or unimplemented subsystems.

| Read next | When |
|-----------|------|
| [README.md](README.md) | Run locally (Git Bash: `bash scripts/run.sh`) |
| [docs/architecture/HIGH_LEVEL.md](docs/architecture/HIGH_LEVEL.md) | System context and containers |
| [docs/architecture/LOW_LEVEL.md](docs/architecture/LOW_LEVEL.md) | Modules, graph routing, schema, APIs |

## Purpose

Evidence-first authoring of clinical/regulatory **document sections**. Generation is subordinate to retrieved, versioned evidence. Unsupported material claims block publication.

## Implemented

| Area | Status |
|------|--------|
| FastAPI + HTML 3-pane review console | Yes |
| Health / ready / metrics | Yes |
| SQLAlchemy evidence store (SQLite default, Postgres URL supported) | Yes |
| Async ingest jobs + worker module | Yes |
| PDF + text parse with page numbers | Yes |
| Structure-aware parent/child chunking | Yes |
| Hybrid BM25 + dense + RRF + heuristic rerank | Yes |
| GraphRAG supersession (in-memory; Neo4j when `NEO4J_URI` set) | Yes |
| Claim extraction + support status + contradictions | Yes |
| Configurable authority tiers 1–6 | Yes |
| Quality gates; critical failure overrides score | Yes |
| LangGraph supervisor; workers never peer-route | Yes |
| HITL interrupt (`RAIP_HITL=required`) and evaluate mode | Yes |
| Fake / Bedrock / Vertex model gateway | Yes |
| Golden evals + 50 injection attacks | Yes |
| Tenant isolation tests | Yes |
| Docker Compose | Yes |
| GitHub Actions CI gates | Yes |
| ADRs, HLA/LLA, security, demo, interview docs | Yes |
| Terraform / K8s / AgentCore / Vertex **sketches** | Interfaces only — not applied |

## Explicitly not implemented

- Production OCR (Tesseract/Textract)
- ClamAV malware farm
- Live OIDC / enterprise IdP
- Pinecone / OpenSearch adapters (interface documented)
- Kafka
- React UI
- Live EHR/FHIR
- HIPAA certification or BAA
- Fabricated evaluation percentages — run the suites

## Honest deltas vs the original plan

- `AuthoringState` is a TypedDict; Pydantic models are the **contracts** (`EvidencePassage`, `ClaimRecord`, gates).
- Local default is SQLite, not Postgres. Postgres+pgvector is Compose / `RAIP_DATABASE_URL`.
- Claims persist as `claims_json` on `drafts`, not separate claim tables.
- Windows Desktop `.venv` is often locked; use `bash scripts/run.sh` or `.\scripts\run.ps1`.

## Verification (local / fake)

```bash
export RAIP_MODEL=fake
export RAIP_HITL=evaluate
bash scripts/with-python.sh -m pytest
bash scripts/with-python.sh -m evals.run_all
bash scripts/with-python.sh -m security.injection_eval
```

Record **actual** numbers from those commands in `evals/reports/latest.json` and `security/reports/injection.json`. Do not edit them by hand to look better.

Measured 2026-08-13 with `RAIP_MODEL=fake`: pytest 20 passed; golden evals 29/29; injection 50/50.

## Ports and env

- Port **8011** (`RAIP_*` prefix)
- CarePath 8007 / HEDIP 8009 remain sibling portfolio apps; RAIP does not import them
