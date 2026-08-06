# Project prompts — R&P Agentic Delivery Fabric

Day-ordered Cursor Composer prompts. Paste each block in order. Keep [`AS_BUILT.md`](AS_BUILT.md) as source of truth.

---

## Day 1 H1 — Graph skeleton + supervisor

> Scaffold `rp-agentic-fabric` with `EngagementState`, LangGraph supervisor loop, and stub workers: `vertical_router`, `compliance_mapper`, `reuse_broker`, `retrieval`, `engagement_synthesizer`, `judge_gate`, `hitl`, `audit_publish`. Workers never route to each other. Pure-logic supervisor routing per AS_BUILT. `RPADF_MODEL=fake` CLI sample engagement prints step_log.

---

## Day 1 H2 — Vertical router + policy packs

> Implement `vertical_router` that classifies `edtech|healthcare|finserv|retail` + sensitivity from the brief. Load `data/policy_packs/{vertical}.yaml` ids. Add taxonomy keywords under `data/verticals/`. Fake LLM must return structured router output.

---

## Day 1 H3 — Compliance mapper

> Implement `compliance_mapper` that emits `guardrail_config` (regs, tool_allowlist, retention_days, hitl_required, forbidden_topics) from the policy pack. No tools run before this node completes.

---

## Day 2 H1 — Reuse broker + KG seed

> Implement `reuse_broker` that selects candidate `AgentComponent` nodes, strips prior tenant embeddings, marks `reusable_ip=true` + `sanitized=true`. Seed `data/kg/seed_entities.jsonl` and `seed_relations.jsonl`. JSONL fallback if Neo4j absent.

---

## Day 2 H2 — Tenant-scoped retrieval

> Implement `retrieval` with hybrid_search + Neo4j lookup/traverse. Max 8 tool calls. Every tool receives `tenant_id`. Filter vectors/Cypher by tenant or reusable_ip. Add mock SIS/FHIR/Salesforce stubs behind allowlist.

---

## Day 2 H3 — Synthesizer + three memory layers

> Implement procedural / episodic / semantic memory modules and `engagement_synthesizer` that drafts an engagement plan citing evidence. Never invent client identifiers from other tenants.

---

## Day 3 H1 — Judge gate

> Implement in-graph `judge_gate` with Compliance, Faithfulness, and Cross-Tenant Leakage scores. Fail → keep approval pending for HITL. Brand/Tone offline only.

---

## Day 3 H2 — HITL + FastAPI cockpit

> Implement `hitl` with `interrupt`. FastAPI Delivery Cockpit on :8002 with demo ingest, pending poll, approve/edit/reject. Healthcare + finserv always HITL.

---

## Day 3 H3 — Audit publish

> Implement `audit_publish` writing immutable audit pack to `data/audit_packs.log` including judge scores, reuse decisions, policy pack id, and client-safe summary (outbound filter blocks foreign tenant ids).

---

## Day 4 H1 — Dual deploy

> Add Bedrock AgentCore and Vertex AI Agent Engine entrypoints under `deploy/` with `build_graph_with_backends(saver, store)`.

---

## Day 4 H2 — Evals + 50-attack suite

> Add LangSmith-ready component/e2e evals and `security/attacks.jsonl` with 50 vertical-specific injection attacks. Pass bar ≥ 95%. Wire `evals/run_all.py`.

---

## Bonus

> Streamlit ops dashboard, Slack notify on failed judges, prompt-refine cron that proposes v+1 without auto-apply.
