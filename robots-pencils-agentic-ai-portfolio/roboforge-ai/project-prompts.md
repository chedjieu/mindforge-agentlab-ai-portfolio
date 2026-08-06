# Project prompts — RoboForge AI

Day-ordered Cursor Composer prompts. Paste each block in order. Keep [`AS_BUILT.md`](AS_BUILT.md) as source of truth. Sibling reference implementation: [`../rp-agentic-fabric`](../rp-agentic-fabric/).

---

## Day 1 H1 — Graph skeleton + supervisor

> Scaffold `roboforge-ai` with `ForgeState`, LangGraph supervisor loop, and stub workers: `intake_analyzer`, `estate_assessor`, `knowledge_builder`, `security_compliance`, `solution_architect`, `roi_optimizer`, `judge_gate`, `hitl`, `delivery_publish`. Workers never route to each other. Pure-logic supervisor routing per AS_BUILT. Port **8003**. `RFAI_MODEL=fake` CLI prints step_log and pauses at HITL.

---

## Day 1 H2 — Intake analyzer

> Implement `intake_analyzer` that extracts objectives, stakeholders, constraints, risks, and domain (`modernize|agentic|rag|migration`) from the intake pack. Hard-block guardrails on injection. Fake LLM returns structured intake.

---

## Day 1 H3 — Estate assessor

> Implement `estate_assessor` with mock AWS inventory + legacy dependency tools (max 8 calls). Emit cloud modernization score and legacy migration notes. Azure/GCP stubs optional read-only.

---

## Day 2 H1 — Knowledge builder + GraphRAG

> Implement `knowledge_builder`: hybrid search over `data/corpus/` + Neo4j/JSONL graph hops. Seed App→API→DataStore→PII→Control relationships. Evidence must carry citation ids.

---

## Day 2 H2 — Security & compliance

> Implement `security_compliance` mapping findings to OWASP/IAM/PII and regs (HIPAA/PCI/SOC2/GDPR as applicable). Emit severity-ranked `security_findings`.

---

## Day 2 H3 — Solution architect + three memories

> Implement procedural / episodic / semantic memory and `solution_architect` that drafts Bedrock AgentCore blueprint + RAG design citing evidence. Never invent cloud resources not in estate/evidence.

---

## Day 3 H1 — ROI optimizer + judge gate

> Implement `roi_optimizer` (token/infra cost, savings, payback) and in-graph `judge_gate` (architecture, groundedness, security-compliance, cost realism). Fail → keep approval pending for HITL.

---

## Day 3 H2 — HITL + Forge Console

> Implement `hitl` with `interrupt`. FastAPI Forge Console on **:8003** with demo ingest, pending poll, approve/edit/reject. HITL always required.

---

## Day 3 H3 — Delivery publish + episodic writeback

> Implement `delivery_publish` writing delivery pack to `data/delivery_packs.log` and appending an episodic lesson for continuous learning.

---

## Day 4 H1 — Dual deploy

> Add Bedrock AgentCore and Vertex AI Agent Engine entrypoints under `deploy/` with `build_graph_with_backends(saver, store)`.

---

## Day 4 H2 — Evals + 50-attack suite

> Add LangSmith-ready component/e2e evals and `security/attacks.jsonl` with 50 attacks (injection, exfil, fake inventory coercion). Pass bar ≥ 95%. Wire `evals/run_all.py`.

---

## Bonus

> Streamlit ops dashboard, architecture diagram export (mermaid), prompt-refine cron proposing v+1 without auto-apply, optional Step Functions batch ingest for large corpora.
