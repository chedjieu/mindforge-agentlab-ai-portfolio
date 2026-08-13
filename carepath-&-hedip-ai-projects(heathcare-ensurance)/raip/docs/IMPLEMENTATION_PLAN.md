# RAIP Engine — Implementation Plan

Build order for the v1 pilot and the next suite slices. Locked as-built: [`../AS_BUILT.md`](../AS_BUILT.md). Design: [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md). HLA/LLA: [architecture/](architecture/).

Reuse CarePath/HEDIP **patterns** (LangGraph supervisor, `*_MODEL=fake`, FastAPI console, injection ≥95%, dual-cloud entrypoints). Do **not** clone CDS or prior-auth domains.

---

## v1 pilot (shipped)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 0 | ADRs, threat model, local vs production matrix, this design set | Done |
| 1 | Foundation: Python 3.12, uv, FastAPI, health/ready/metrics, SQLAlchemy, Docker Compose | Done |
| 2 | Evidence store + ingest: upload, MIME/hash, pypdf pages, parent/child chunking, job worker | Done |
| 3 | Hybrid retrieval: BM25 + dense + RRF + rerank + tenant filters | Done |
| 4 | GraphRAG supersession + claim–evidence edges (Neo4j optional) | Done |
| 5 | Grounding engine + LangGraph supervisor + quality/publication gates | Done |
| 6 | 3-pane review console + HITL (`required` / `evaluate`) | Done |
| 7 | Golden evals, 50-attack injection ≥95%, tenant tests, GitHub Actions | Done |
| 8 | Deploy **sketches** (AgentCore / Vertex / Terraform / K8s interfaces) | Done (not applied) |

### v1 acceptance

```bash
export RAIP_MODEL=fake
export RAIP_HITL=evaluate
bash scripts/with-python.sh -m pytest
bash scripts/with-python.sh -m evals.run_all
bash scripts/with-python.sh -m security.injection_eval
bash scripts/run.sh
```

Open http://127.0.0.1:8011 and complete the four demos: golden, PDF injection, supersession, unsupported claim. See [demo/DEMO.md](demo/DEMO.md).

On Windows, do **not** rely on `uv run` / `uv sync` if `.venv\Scripts\python.exe` is Access denied — use `scripts/with-python.ps1`.

---

## Honest deltas vs the original delivery plan

- `AuthoringState` is a TypedDict; Pydantic models are the **contracts**.
- Local default is SQLite; Postgres+pgvector via Compose / `RAIP_DATABASE_URL`.
- Claims persist as `claims_json` on `drafts`, not separate claim tables.
- OCR is detection-only; malware scan is MIME/size/hash.

Do not regress: workers never peer-route; never invent citations; critical safety failure overrides aggregate score; source PDFs are untrusted data.

---

## Next slices (suite thesis — risk adjustment)

Land on the **existing** evidence store and publication gate. Do not start a fourth package.

1. Treat HCC / RAF narratives as document types with synthetic CMS/coding-policy PDFs and templates.
2. Claim-level support status for diagnosis-to-HCC mappings — block unsupported codes (`EVIDENCE GAP`).
3. Gap-list notes that HEDIP pop-health / RCM can describe; RAIP publishes only if evidence supports the gap.
4. Do **not** ship a production CMS-HCC model, live claims feed, or NCQA-certified calculator in this phase.

Scale path after that: [architecture/PILOT_TO_SCALE.md](architecture/PILOT_TO_SCALE.md) (controlled expansion → enterprise).
