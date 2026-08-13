# CarePath AI — Execution Plan

**Folder:** `carepath-ai/`  
**Product:** CarePath AI — AI-driven patient care pathway and clinical decision support  
**Port:** `8007` · **Env:** `CAREPATH_*` · **Python:** 3.12 (`>=3.11,<3.13`)

Sister of [HEDI Platform](plan-hedip.md) (quality / decision intelligence) and [RAIP Engine](plan-raip.md) (risk adjustment / evidence authoring). Suite overview: [plan-overview.md](plan-overview.md).

CarePath stays **clinical-only** and **standalone**. HEDIP must not become a runtime dependency.

---

## Problem

Clinicians need personalized treatment plans for patients with complex histories, multiple chronic conditions, medication interactions, and stated preferences — with safety gates before any plan is published.

| ID | Actor | Use case |
|----|-------|----------|
| UC1 | Clinician | Draft a plan for a diabetic + hypertensive patient with 6 active meds |
| UC2 | Clinician | Re-run after the patient rejects a medication class |
| UC3 | Clinical reviewer | HITL approve / edit / reject before mock-EHR publish |
| UC4 | Platform eng | Ship only if safety judge + injection suite pass |

**Non-goals v1:** live FHIR/EHR, real RxNorm/FDA APIs, SSO, insurance prior-auth, HIPAA production hardening.

---

## Architecture (locked)

LangGraph supervisor loop. Workers **never** route to each other.

```text
START → firewall → supervisor
  ├─ patient_data_extractor            → supervisor
  ├─ medication_interaction_checker    → supervisor
  ├─ treatment_plan_generator          → supervisor
  ├─ patient_preference_agent          → supervisor
  ├─ treatment_plan_evaluator (judge)  → supervisor
  ├─ hitl                              → supervisor
  └─ plan_publish                      → END
```

| Layer | Choice |
|-------|--------|
| RAG | Hybrid BM25 + dense + Neo4j GraphRAG (`NEO4J_URI` or JSONL KG) |
| Memory | Procedural / episodic / semantic |
| Models | Bedrock / Vertex via gateway; `CAREPATH_MODEL=fake` for CI |
| Safety | Firewall + med checker + judge + HITL + injection suite ≥ 95% |
| UI | FastAPI clinician console |
| Deploy | `deploy/agentcore` + `deploy/vertex_engine` |

---

## As-built status

v1 scaffold is **shipped**: docs, graph, workers, HITL, console, golden evals, injection suite, dual-cloud entrypoints. See [`carepath-ai/AS_BUILT.md`](../carepath-ai/AS_BUILT.md).

## Golden demo

Patient **P001** (T2DM + HTN + 6 meds). Prefer non-injectable pathway. Approve HITL to publish.

```powershell
cd carepath-ai
uv sync --python 3.12
$env:CAREPATH_MODEL = "fake"
uv run python -m app.graph
uv run python -m app.main
```

Open http://127.0.0.1:8007

Infra: workspace `docker compose up -d` maps CarePath Postgres **5435** and Neo4j **7475 / 7688**.

---

## Follow-ons (do not regress v1)

- Shared composite `uv` + ruff + pytest action with HEDIP / RAIP
- Nightly LangSmith evals on non-fake models
- Dependency audit gate in CI
- Keep citations on clinical claims; HITL before publish
