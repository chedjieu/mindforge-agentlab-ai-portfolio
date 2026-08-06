# As-Built — CarePath AI (Personalized Treatment Plan Platform)

**Package:** `carepath-ai` v0.1.0  
**UI:** Clinician Console at `http://127.0.0.1:8007`

---

## Purpose

Multi-agent clinical decision-support system that generates personalized treatment plans for patients with complex medical histories and multiple chronic conditions. A LangGraph **supervisor loop** coordinates EHR extraction, medication interaction checking, plan generation, preference incorporation, and a safety judge, then pauses for clinician HITL before publishing to a mock EHR. Dual deploy: **Bedrock AgentCore** and **Vertex AI Agent Engine**.

---

## Locked decisions

| Area | Decision |
|------|----------|
| Orchestration | LangGraph **supervisor loop** — workers never route to each other |
| Workers | `patient_data_extractor` → `medication_interaction_checker` → `treatment_plan_generator` → `patient_preference_agent` → `treatment_plan_evaluator` → `hitl` → `plan_publish` |
| Judges | `treatment_plan_evaluator` (LLM ∩ heuristics); cross-provider vs generator |
| HITL | Always required for v1 (clinical = sensitive); `langgraph.types.interrupt` |
| Chat models | Bedrock primary / Vertex swap via `CAREPATH_MODEL`; `fake` for offline/CI |
| Judge model | Cross-provider via `CAREPATH_JUDGE_MODEL` |
| Embeddings | Titan / Vertex / fake hashed vectors |
| Vector / hybrid | Local hybrid (BM25-style + dense) over `data/corpus`; Chroma optional |
| GraphRAG | Neo4j when `NEO4J_URI` set; else JSONL seeds in `data/kg/` |
| Memory | Procedural protocols + episodic patient history + semantic store |
| Checkpointer | Sqlite local → `checkpoints.sqlite`; Postgres via `POSTGRES_DSN` |
| Deploy | `deploy/agentcore` + `deploy/vertex_engine` |
| Evals | LangSmith-ready; injection suite **≥ 95%** on 50 attacks |
| UI | FastAPI + fetch-polled clinician console — no React/npm |
| Port | **8007** |
| Explicitly not v1 | Live FHIR/EHR, RxNorm/FDA APIs, insurance prior-auth, HIPAA production hardening |

### Composer constraints (do not regress)

1. Workers never call each other — only the supervisor routes.  
2. Clinical plans always require HITL before publish.  
3. Factual claims require citations from retrieved evidence or KG paths.  
4. Judge model should be cross-provider vs the generator when both cloud providers are configured.  
5. Injection suite must stay ≥95% before deploy promote.  
6. Major medication interactions must be surfaced before plan generation completes.

---

## Graph flow

```
START → firewall → supervisor
          ├─ patient_data_extractor        → supervisor
          ├─ medication_interaction_checker → supervisor
          ├─ treatment_plan_generator        → supervisor
          ├─ patient_preference_agent        → supervisor
          ├─ treatment_plan_evaluator        → supervisor  (may clear draft → revise)
          ├─ hitl                            → supervisor  (interrupt)
          ├─ plan_publish                    → supervisor
          └─ END
```

| Route condition | Next |
|-----------------|------|
| `blocked` | `plan_publish` (refusal) |
| `approval == "rejected"` | `END` |
| `patient_profile is None` | `patient_data_extractor` |
| `medication_review is None` | `medication_interaction_checker` |
| `draft_plan is None` | `treatment_plan_generator` |
| preferences present and not applied | `patient_preference_agent` |
| `safety_score is None` | `treatment_plan_evaluator` |
| judge revise and `revise_count < 2` | clear draft → `treatment_plan_generator` |
| `approval == "pending"` | `hitl` |
| approved/edited and not published | `plan_publish` |
| else | `END` |

---

## Verification checklist

- [x] `CAREPATH_MODEL=fake` e2e golden P001 produces cited plan + med alerts  
- [x] HITL approve writes mock publish log entry  
- [x] Preference agent removes injectable pathway for P001  
- [x] `python -m evals.run_all` passes (3/3 golden)  
- [x] `python -m security.injection_eval` ≥ 95%  
- [x] AgentCore + Vertex entrypoints import and run fake smoke  
