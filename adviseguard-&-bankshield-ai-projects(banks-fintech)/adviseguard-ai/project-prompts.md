# AdviseGuard AI — Cursor Composer Prompt Library

Paste in order. **AS_BUILT wins** on conflicts. Package lives at `10.adviseguard-&-bankshield-ai-projects/adviseguard-ai/`.

---

## Day 1 H1 — Scaffold + docs

```
Scaffold adviseguard-ai under 10.adviseguard-&-bankshield-ai-projects with pyproject, docker-compose (Neo4j 7688, Postgres 5435), .env.example, AS_BUILT.md, docs/SYSTEM_DESIGN.md, README.md. LangGraph supervisor only; FastAPI :8004; ADVISEGUARD_* env prefix; fake offline path. No React.
```

## Day 1 H2 — State + models + guardrails

```
Implement SessionState, llm/_fake_llm factories, guardrails (hard-block + escalate + PII mask). Intents: advice|fraud|support|mixed.
```

## Day 2 H1 — Synthetic data + ingest + hybrid search

```
scripts/generate_synthetic_fin_data.py + ingest to Chroma adviseguard_chunks + BM25/RRF hybrid_search. Corpus domains per AS_BUILT.
```

## Day 2 H2 — Neo4j tools

```
Graph tools with MERGE load and JSON fallback; SUITABLE_FOR / SHARES_DEVICE / MATCHES_PATTERN; budget ≤6.
```

## Day 3 H1 — Supervisor + specialists

```
Supervisor pure routing + intent_router + financial_advisor + fraud_detector + customer_support. Node names must not collide with state keys.
```

## Day 3 H2 — Retriever + judges + synthesizer

```
hybrid_retriever, compliance_judge, risk_judge, synthesizer with revise budget 2 and HITL forcing rules.
```

## Day 4 H1 — HITL + publish

```
hitl interrupt + response_publish to data/published_responses.log.
```

## Day 4 H2 — FastAPI dual UI

```
/ customer console, /ops fraud dashboard, /ask, /ask/demo-advice, /fraud/demo, /pending, /approve, /case.
```

## Day 5 — Evals + 50-attack suite

```
evals/run_all.py + security/attacks.jsonl (50) pass ≥95%.
```

## Bonus — Deploy stubs

```
agentcore_entrypoint.py + deploy/*.sh for AgentCore/Vertex; keep fake local path.
```
