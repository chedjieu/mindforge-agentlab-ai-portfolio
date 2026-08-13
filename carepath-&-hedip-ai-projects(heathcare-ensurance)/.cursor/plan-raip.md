# RAIP Engine — Execution Plan

**Folder:** `raip/` (formerly `reguMed-authoring-platform/`)  
**Product:** RAIP Engine — Risk Adjustment & Quality Incentive Processing Platform  
**As-built name:** ReguMed Authoring Intelligence Platform  
**Port:** `8011` · **Env:** `RAIP_*` · **Python:** `>=3.12,<3.14`

Sister of [CarePath AI](plan-carepath-ai.md) (care pathways) and [HEDI Platform](plan-hedip.md) (quality / HEDIS). Suite overview: [plan-overview.md](plan-overview.md).

Reuse CarePath/HEDIP **patterns**. Do **not** clone CDS or prior-auth domains.

---

## Suite thesis vs as-built

| Lens | Description |
|------|-------------|
| **Suite role** | RAF scoring support, HCC coding validation, quality-incentive gap analysis, defensible documentation |
| **As-built v1** | Evidence-first **authoring**: section drafts from approved PDFs/templates with claim-level provenance, supersession, contradiction detection, and publication blocking |

Risk-adjustment features must sit **on** the evidence store and publication gate. Unsupported HCC/RAF statements must not publish — same rule as clinical claims.

---

## Design principle

If the platform cannot establish sufficient evidence for a statement, it must not confidently generate that statement. Prefer `EVIDENCE GAP` over an unsupported claim.

## Locked decisions

| Area | Decision |
|------|----------|
| Orchestration | LangGraph supervisor; workers never peer-route |
| Port / env | **8011** / `RAIP_*` |
| Models | `RAIP_MODEL` / `RAIP_JUDGE_MODEL` / `RAIP_EMBEDDINGS`; `fake` for CI |
| Data | SQLite default; Postgres + pgvector via Docker |
| Graph | Neo4j when `NEO4J_URI` set; else JSONL/in-memory |
| HITL | Required for demo; `evaluate` skips interrupt for evals |
| Safety | Critical safety failure **overrides** aggregate quality score |
| PHI | Synthetic only. No HIPAA certification claim |

## Agent nodes (v1)

`firewall` → `supervisor` ↔ retrieval, synthesis, drafting, claim_verification, quality_gates, editorial, publication_gate, hitl → persist → END

Regulatory / template / safety / security are **gate functions**, not extra chat agents.

---

## As-built status

Pilot v1 is **shipped** (ingest, hybrid retrieval, GraphRAG supersession, grounding, console, evals). See [`raip/AS_BUILT.md`](../raip/AS_BUILT.md).

```bash
cd raip
bash scripts/sync.sh
bash scripts/run.sh
```

Open http://127.0.0.1:8011

Workspace compose includes RAIP Postgres **5432**, Neo4j **7474 / 7687**, API **8011**, and worker. API/worker images need `psycopg2` before they stay up; local `scripts/run.sh` is the supported Windows path.

**Demos:** golden (metformin-first), PDF injection, guideline supersession, unsupported-claim block.

---

## Next slices (risk adjustment)

1. Treat HCC / RAF narratives as **document types** with templates and approved CMS/coding-policy PDFs (synthetic in v1).
2. Claim-level support status for diagnosis-to-HCC mappings — block unsupported codes.
3. Gap list that HEDIP pop-health / RCM domains can describe; RAIP only publishes if evidence supports the gap.
4. Do not ship a production CMS-HCC model or live claims feed in v1.

## Acceptance (do not regress)

```text
RAIP_MODEL=fake
pytest
python -m evals.run_all
python -m security.injection_eval
```

Injection detection target: **≥ 95%**. Metrics in reports are measured, never invented.
