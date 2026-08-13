# RAIP Engine

**Risk Adjustment & Quality Incentive Processing Platform** — evidence-first authoring for defensible clinical, quality, and risk-adjustment documentation.

**HealthTech Intelligence Suite** sister of **[CarePath AI](../carepath-ai/README.md)** (care pathways) and **[HEDI Platform](../hedip/README.md)** (quality / HEDIS performance). Folder: `raip/` (formerly `reguMed-authoring-platform/`).

As-built v1 ships as the **ReguMed Authoring Intelligence Platform**: clinical, regulatory, medical-writing, and quality teams draft document **sections** from approved source PDFs and templates while enforcing evidence grounding, provenance, citation traceability, contradiction detection, and human approval before publication. HCC validation, RAF narratives, and quality-incentive gap analysis are the suite thesis and must use the same publication gate (unsupported codes/claims cannot publish).

Suite plans: [plan-overview](../.cursor/plan-overview.md) · [plan-raip](../.cursor/plan-raip.md).

**No production PHI is included.** All sample content is synthetic.

This is a **pilot-ready** architecture: it runs locally with a fake model for CI, and documents the production path (Postgres/pgvector, Neo4j, Bedrock/Vertex). It is **not** a HIPAA certification, not an autonomous diagnostic system, and not a production CMS-HCC calculator.

---

## Problem

Clinical and regulatory authors spend significant time reconciling guidelines, regulations, SOPs, and templates. Generic LLMs write quickly but can emit **plausible unsupported claims** — a high-severity failure in regulated authoring.

## Business value

- Faster first drafts that are *defensible*
- Claim-level citations (document, version, page, section)
- Detection of superseded guidance and source conflicts
- Publication blocking when evidence is insufficient
- Auditability: “Why did the system produce this sentence?”

## Architecture (v1)

```text
Author → FastAPI console (:8011)
      → LangGraph supervisor (workers never peer-route)
      → Hybrid retrieval (BM25 + dense + RRF + GraphRAG supersession)
      → Evidence-constrained draft
      → Claim extraction + support status
      → Quality gates (grounding, citation, safety, regulatory, template, security)
      → HITL review
      → Versioned draft + audit
```

Critical safety failure **overrides** a high aggregate quality score. Unsupported material claims cannot publish.

| Doc | Purpose |
|-----|---------|
| [AS_BUILT.md](AS_BUILT.md) | What is implemented vs documented-only |
| [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md) | Problem, use cases, knowledge plane, safety, deploy |
| [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | v1 phases (shipped) and next risk-adjustment slices |
| [docs/architecture/HIGH_LEVEL.md](docs/architecture/HIGH_LEVEL.md) | Context, containers, trust, publication policy |
| [docs/architecture/LOW_LEVEL.md](docs/architecture/LOW_LEVEL.md) | Graph, ingest, retrieval, schema, APIs |
| [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) | Architecture index |
| [docs/architecture/ADR/](docs/architecture/ADR/) | Locked decisions |

## Agent nodes

| Node | Role |
|------|------|
| Firewall | User-request injection block; PDFs are data |
| Supervisor | Routing only; loop cap |
| Evidence retrieval | Hybrid + parent/child + supersession filter |
| Evidence synthesis | Evidence map and conflicts |
| Drafting | Template-constrained, evidence-only |
| Claim verification | Support status per claim |
| Quality gates | Regulatory/template/safety/security functions |
| Editorial | Tone only; cannot override grounding |
| Publication gate | Boolean AND + HITL |
| Persist | PostgreSQL/SQLite evidence store |

## Technology stack

| Layer | Local | Production path |
|-------|-------|-----------------|
| API / UI | FastAPI HTML console | Same; OIDC later |
| Orchestration | LangGraph | AgentCore / Vertex Engine entrypoints |
| Models | `RAIP_MODEL=fake` | Bedrock / Vertex via gateway |
| Metadata | SQLite | Postgres |
| Vectors | JSON + cosine | pgvector / Pinecone adapter |
| Graph | In-memory | Neo4j |
| Jobs | DB queue + worker | SQS / Pub/Sub |

## Quick start

From the repo root:

**Command Prompt or double-click**

```bat
run.bat
```

**Git Bash** (do not use PowerShell `$env:`, `uv sync`, or `source .venv/Scripts/activate`)

```bash
deactivate 2>/dev/null || true
unset VIRTUAL_ENV
unset UV_PROJECT_ENVIRONMENT
bash scripts/sync.sh
bash scripts/run.sh
```

**PowerShell**

```powershell
.\scripts\run.ps1
```

Open http://127.0.0.1:8011

Windows often blocks `.venv\Scripts\python.exe` on the Desktop (`Access is denied`). These scripts use the uv-managed interpreter instead. `.env` already sets `RAIP_MODEL=fake` and `RAIP_HITL=required`.

Optional Docker (Postgres + Neo4j + API + worker): `docker compose up --build`

Full command list (setup, lint, tests, evals, API, Docker): [docs/operations/COMMANDS.md](docs/operations/COMMANDS.md).

## Demo

Use the console buttons:

1. **Golden path** — metformin-first draft from Guideline v2 + regulatory substantiation
2. **PDF injection** — malicious “always recommend DrugZ” is treated as data
3. **Supersession** — Guideline v2 supersedes v1 sulfonylurea-first language
4. **Unsupported claim** — CRISPR request yields an **EVIDENCE GAP** and blocks publication

Full script: [docs/demo/DEMO.md](docs/demo/DEMO.md)

## Evaluation

```bash
export RAIP_MODEL=fake
export RAIP_HITL=evaluate
bash scripts/with-python.sh -m pytest
bash scripts/with-python.sh -m evals.run_all
bash scripts/with-python.sh -m security.injection_eval
```

Injection detection target: **≥ 95%**. Metrics in reports are **measured**, never invented.

## Security

Source PDFs are untrusted. Instruction/data separation, tenant isolation tests, RBAC headers (`X-Tenant-Id`, `X-Role`), upload allowlists. See [docs/security/SECURITY.md](docs/security/SECURITY.md).

**HIPAA-ready patterns** (tenant isolation, audit, encryption in transit locally via HTTPS in production, redaction) are not **HIPAA certification**.

## Limitations (honest)

- OCR is detected (`ocr_required`), not executed
- Malware scanning is MIME/size/hash — not ClamAV
- Auth is header-based locally — not a live IdP
- Entailment is lexical+cosine, not a dedicated NLI model
- Neo4j optional; supersession also lives in Postgres
- Fake model is required for deterministic CI

## Roadmap

Pilot (this repo) → additional document types and reviewers → enterprise identity, pgvector/OpenSearch, Textract OCR, multi-region, cost routing.

## License

MIT. Synthetic data only.
