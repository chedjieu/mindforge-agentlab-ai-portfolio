# As-Built — CarePath AI & HEDIP Workspace

**Workspace:** CarePath AI + HEDIP (healthcare / insurance agentic platforms)  
**Packages:** `carepath-ai` v0.1.0 · `hedip` v0.1.0  
**UIs:** CarePath Clinician Console `8007` · HEDIP Command Center `8009`

Per-project detail: [carepath-ai/AS_BUILT.md](carepath-ai/AS_BUILT.md) · [hedip/AS_BUILT.md](hedip/AS_BUILT.md).

---

## Purpose

This workspace holds two sibling interview-grade / portfolio systems that share the same platform stack (LangGraph orchestration, hybrid RAG, Neo4j GraphRAG, memory layers, firewall + judges, HITL, dual-cloud deploy) but different product scopes:

| System | Scope |
|--------|--------|
| **CarePath AI** | Clinical-only personalized treatment plan generation for complex chronic-care patients |
| **HEDIP** | Umbrella multi-domain decision intelligence: prior auth, claims, CDS, care coord, knowledge, fraud, pop health, RCM |

---

## Locked workspace decisions

| Area | Decision |
|------|----------|
| Relationship | **Siblings** — HEDIP does not import or call `carepath-ai`; CDS is reimplemented inside HEDIP |
| Orchestration | LangGraph supervisors; workers never peer-route |
| Ports | CarePath **8007** · HEDIP **8009** (reserve 8008 for a possible thin PA-only split) |
| Env prefixes | `CAREPATH_*` vs `HEDIP_*` (no shared env namespace) |
| Offline / CI | `*_MODEL=fake` on both |
| Judges | Cross-provider when both Bedrock and Vertex are configured |
| RAG | Hybrid BM25 + dense; Neo4j when `NEO4J_URI` set, else JSONL KG seeds |
| Memory | Procedural + episodic + semantic (each package owns its stores) |
| UI | FastAPI + fetch-polled consoles — no React/npm in v1 |
| Deploy | `deploy/agentcore` + `deploy/vertex_engine` in each package |
| Safety bar | Injection suite **≥ 95%** before promote |
| Explicitly not v1 | Live EHR, real CMS/PBM, Kafka-in-path, HIPAA prod hardening |

### Constraints (do not regress)

1. Workers never call each other — only supervisors / domain routers.  
2. Sensitive clinical / payer decisions always require HITL before publish.  
3. Factual / policy / clinical claims require citations from retrieval or KG paths.  
4. CarePath stays standalone; HEDIP must not become a runtime dependency of CarePath or vice versa.  
5. Injection suites stay ≥95% on both packages before deploy promote.

---

## Platform stack (shared pattern)

```
UI (FastAPI console)
  → firewall
  → supervisor / intent router
  → domain or worker agents
  → hybrid RAG + GraphRAG tools
  → memory (procedural / episodic / semantic)
  → LLM-as-judge (cross-provider)
  → HITL interrupt (sensitive paths)
  → publish / audit
```

| Layer | Tech |
|-------|------|
| Orchestration | LangGraph |
| Models | Bedrock / Vertex / `fake` via gateway env vars |
| RAG | Local hybrid over `data/corpus`; Chroma optional |
| GraphRAG | Neo4j or `data/kg/` JSONL |
| Checkpointer | Sqlite local; Postgres via `POSTGRES_DSN` |
| Evals | Golden scenarios + `security/injection_eval` |
| Infra sketch | `infra/compose/docker-compose.yml` per package |

---

## CarePath AI (summary)

**Flow:** firewall → supervisor → extract → med check → plan → preferences → evaluator → HITL → publish.

**Workers:** `patient_data_extractor`, `medication_interaction_checker`, `treatment_plan_generator`, `patient_preference_agent`, `treatment_plan_evaluator`, `hitl`, `plan_publish`.

**Verified:** fake e2e on P001, HITL publish log, preference path, goldens 3/3, injection ≥95%, dual deploy smoke.

---

## HEDIP (summary)

**Flow:** firewall → intent router → master supervisor → one domain subgraph → shared judge → HITL? → publish.

**Domains (v1):**

| Depth | Domains |
|-------|---------|
| Full | `prior_auth`, `claims`, `clinical_cds`, `knowledge` |
| Thin | `care_coord`, `fraud`, `pop_health`, `rcm` |

**HITL required:** prior_auth, claims, clinical_cds, fraud (investigate).

**Verified:** fake smoke across domains, goldens for PA / Claims / CDS / Knowledge, thin structured outputs, injection ≥95%, dual deploy smoke.

---

## Workspace verification checklist

- [x] Root `README.md` and `AS_BUILT.md` present  
- [x] Each package has its own README, AS_BUILT, SYSTEM_DESIGN, ARCHITECTURE  
- [x] Ports do not collide (8007 / 8009)  
- [x] Env prefixes isolated (`CAREPATH_*` / `HEDIP_*`)  
- [x] No runtime coupling between packages  
- [x] Both packages pass fake goldens + injection ≥95% (see package AS_BUILT checklists)

---

## Doc map

| Doc | Location |
|-----|----------|
| Workspace README | [README.md](README.md) |
| Workspace as-built | this file |
| CarePath README / as-built | [carepath-ai/README.md](carepath-ai/README.md), [carepath-ai/AS_BUILT.md](carepath-ai/AS_BUILT.md) |
| CarePath design | [carepath-ai/docs/](carepath-ai/docs/) |
| HEDIP README / as-built | [hedip/README.md](hedip/README.md), [hedip/AS_BUILT.md](hedip/AS_BUILT.md) |
| HEDIP design | [hedip/docs/](hedip/docs/) |
| Plans | [.cursor/plans/](.cursor/plans/) |
