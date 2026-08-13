# HEDI Platform (HEDIP) — Execution Plan

**Folder:** `hedip/`  
**Product:** HEDI Platform — Healthcare Effectiveness Data & Information Performance Engine  
**Port:** `8009` · **Env:** `HEDIP_*` · **Python:** 3.12 (`>=3.11,<3.13`)

Sister of [CarePath AI](plan-carepath-ai.md) (care pathways) and [RAIP Engine](plan-raip.md) (risk adjustment / evidence). Suite overview: [plan-overview.md](plan-overview.md).

HEDIP **reuses CarePath patterns** and includes a clinical CDS domain with equivalent capability. It does **not** import or call `carepath-ai`.

---

## Suite thesis vs as-built

| Lens | Description |
|------|-------------|
| **Suite role** | Quality-measure and HEDIS-oriented performance: gaps, compliance reporting, population effectiveness |
| **As-built v1** | Umbrella **Healthcare Decision Intelligence Platform** — one supervisor, many payer/provider domains |

Quality / HEDIS work should land on the existing `pop_health`, `claims`, `rcm`, and `knowledge` domains rather than a fourth package.

---

## Locked decisions

| Area | Decision |
|------|----------|
| Scope v1 | Umbrella platform; single-domain per request |
| Orchestration | Master supervisor → intent router → domain subgraph; workers never peer-route |
| Depth | **Full:** prior auth, claims, clinical CDS, knowledge. **Thin but runnable:** care coord, fraud, pop health, RCM |
| HITL | Required for PA decisions, claim submit advice, fraud escalate, clinical publish |
| UI | FastAPI Command Center — domain picker + shared evidence / judge / HITL |
| Explicitly not v1 | Live Epic/Cerner, real CMS/PBM APIs, Kafka-in-path, HIPAA prod hardening |

---

## Domain catalog

| Domain | Workflow | Depth |
|--------|----------|-------|
| `prior_auth` | Evidence → policy → guidelines → formulary → approve/deny/need_info | Full |
| `claims` | ICD/CPT → coverage → denial risk → appeal draft | Full |
| `clinical_cds` | CarePath-parity treatment plan | Full |
| `knowledge` | Cited enterprise Q&A | Full |
| `care_coord` | Discharge tasks and escalation | Thin |
| `fraud` | Graph score + investigator brief | Thin |
| `pop_health` | Risk tier + actions (HEDIS/quality hook) | Thin |
| `rcm` | ICD/CPT draft + coding gaps | Thin |

---

## As-built status

Umbrella v1 is **shipped**. See [`hedip/AS_BUILT.md`](../hedip/AS_BUILT.md).

```powershell
cd hedip
uv sync --python 3.12
$env:HEDIP_MODEL = "fake"
uv run python -m app.graph
uv run python -m app.main
```

Open http://127.0.0.1:8009

Infra: workspace `docker compose up -d` maps HEDIP Postgres **5436** and Neo4j **7476 / 7689**.

---

## Next slices (quality engine)

1. Golden paths that look like HEDIS measures (diabetes control, medication adherence, follow-up after hospitalization) using synthetic members.
2. Gap-in-care output that CarePath can consume as a *narrative* (copy, not an API).
3. Coding-gap handoff notes that RAIP can ground against approved policy PDFs.
4. Do not add a live NCQA/HEDIS certified calculator in v1 — document the production path honestly.
