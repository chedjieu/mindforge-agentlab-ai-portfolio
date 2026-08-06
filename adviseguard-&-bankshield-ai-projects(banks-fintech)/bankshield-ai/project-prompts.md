# BankShield AI — Cursor Composer Prompt Library

Paste prompts **in order**. Locked decisions live in [`AS_BUILT.md`](AS_BUILT.md); when prompts and runtime diverge, **AS_BUILT wins**.

Reference patterns: sibling `7.enterprise-ai-knowledge-platform`.

---

## Day 1 H1 — Scaffold + locked docs

```
Create BankShield AI in this repo root as package bankshield-ai v0.1.0 (EGKP-style).

Deliverables:
- pyproject.toml (Python 3.11–3.12, FastAPI, LangGraph, LangChain, Chroma, Neo4j, pydantic, dotenv, uvicorn)
- .env.example + docker-compose.yml (Neo4j :7687, Postgres+pgvector :5434)
- AS_BUILT.md, docs/SYSTEM_DESIGN.md, README.md
- app/ package skeleton: env.py, state.py (InvestigationState), guardrails.py, llm.py, _fake_llm.py, graph.py stub, agents/, tools/, ingest/, ui/

Locked:
- LangGraph supervisor loop only; workers never route to each other
- Env prefix BANKSHIELD_*
- UI port 8003, no React/npm
- Deep tooling: wire/ACH, sanctions/AML, mule graph; shallow: card/ATO/APP/BEC/instant_pay
- Fake model offline path required
```

---

## Day 1 H2 — State, config, model factory

```
Implement InvestigationState and model factory for BankShield.

- app/state.py: fraud_types, payment_rail, needs_graph/identity, entities, identity_findings, txn_features, evidence, graph_paths, reg_citations, similar_cases, risk_score/band, recommendation, grounding_score, revise_count, approval, sar_draft, published, step_log, next
- Route literals for all workers + END
- app/llm.py: get_chat_model / get_embeddings reading BANKSHIELD_MODEL / BANKSHIELD_EMBEDDINGS; Bedrock + Vertex + fake; throttle → fake fallback
- app/_fake_llm.py: deterministic hashed embeddings + structured_output defaults for fraud triage
- app/guardrails.py: HARD_BLOCK + ESCALATE patterns + mask_pii + GUARDRAIL_REFUSAL behavior

Do not implement full workers yet beyond stubs if needed for imports.
```

---

## Day 2 H1 — Synthetic data + ingest + Chroma/BM25

```
Add synthetic bank data and ingest pipeline.

- scripts/generate_synthetic_bank_data.py: ≥20 alerts spanning wire/ACH/card/ATO/mule/sanctions/APP/BEC/instant_pay; gold mule ALT-MULE-001 and sanctions ALT-OFAC-001; KYC profiles; corpus markdown with YAML frontmatter domains; data/kg/mule_ring.json; past_investigations.jsonl; prompts
- app/ingest/pipeline.py: load → chunk → embed (default fake) → Chroma collection bankshield_chunks; optional Neo4j MERGE
- app/tools/hybrid_search.py: dense + BM25 + RRF + rerank; EMPTY_CHUNK sentinel

Run generate + ingest offline successfully.
```

---

## Day 2 H2 — Neo4j schema + mule-ring tools

```
Implement GraphRAG tools for mule networks.

- app/tools/neo4j_graph.py: load_kg_seeds_to_neo4j (MERGE), find_shared_entity_paths, detect_mule_ring
- Max 6 tool calls budget constant
- JSON seed in-memory fallback when Neo4j unavailable
- Relationships: OWNS, TRANSFERRED_TO, SHARES_DEVICE, SHARES_IP, SHARES_PHONE, SHARES_BENEFICIARY, RELATED_TO
- Wire app/tools/kyc_mock.py and txn_features.py for identity + wire/ACH deep features
```

---

## Day 3 H1 — Supervisor + triage/identity/transaction

```
Wire LangGraph star topology and first workers.

- app/agents/supervisor.py: pure if/elif routing per AS_BUILT (no LLM)
- app/graph.py: build_graph / build_graph_with_backends / make_initial_state / get_alert
- Workers: triage_router (guardrail + heuristic/LLM), identity_kyc, transaction_intel
- Always set progress sentinels so the loop cannot stall on empty lists forever
- CLI __main__ on app.graph runs ALT-MULE-001
```

---

## Day 3 H2 — Regulatory RAG + similar cases + risk scorer

```
Add retrieval and scoring workers.

- regulatory_rag: hybrid_search across aml_policy/ofac_guidance/fraud_playbooks + live_feed_fixture merge; EMPTY sentinel
- similar_case_retriever node (state key remains `similar_cases`): vector search closed_cases/sar_examples
- risk_scorer: fuse ml stub, txn, behavior, synthetic, mule, ofac, graph density → risk_band
- OFAC hits force score ≥ 0.9 and sanctions fraud type
```

---

## Day 4 H1 — Recommender + grounder + HITL + SAR

```
Complete the decision path.

- recommender: Pydantic structured recommendation with evidence_ids, regulatory_refs, graph_explanation, similar_case_ids, confidence, reasoning; force HITL for high/critical or wire/sanctions/aml/mule
- grounder_judge: claim–evidence score; revise by clearing recommendation up to 2 times; optional cross-provider judge_client
- hitl: interrupt-only node; approve/edit/reject; log outcomes
- sar_publisher: mask PII, draft SAR package, append data/published_cases.log, published=True
```

---

## Day 4 H2 — FastAPI investigator UI

```
Ship investigator console on :8003.

- app/main.py: /alerts, /investigate, /investigate/demo, /investigate/demo-sanctions, /threads, /pending, /case/{id}, /approve/{id}, /ask
- app/ui/investigator.html + styles.css: alert queue, threads, HITL cards, case JSON detail
- Background tasks for stream-until-interrupt and Command(resume=...)
- Offline fake model defaults
```

---

## Day 5 — Evals + injection + polish

```
Add quality gates.

- evals/: groundedness_judge, citation_coverage, risk_consistency, e2e_eval, run_all.py
- security/attacks.jsonl (20) + injection_eval.py pass ≥ 95%
- Ensure docker-compose + README quick start work
- Confirm mule + sanctions demos HITL then publish SAR after approve
```

---

## Bonus — Deploy stubs

```
Add AgentCore + Vertex deploy stubs without breaking local fake path.

- agentcore_entrypoint.py using PostgresSaver when POSTGRES_DSN set
- deploy/deploy_agentcore.sh and deploy/deploy_vertex_engine.sh documentation stubs
- Keep DISABLE_AGENTCORE_MEMORY=1 by default
```
