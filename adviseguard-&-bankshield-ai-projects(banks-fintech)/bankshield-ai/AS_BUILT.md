# As-Built Planning Document

## Project title

**BankShield AI** — Multi-Agent Financial Crime Investigation Platform

Package: `bankshield-ai` v0.1.0  
Location: `10.adviseguard-&-bankshield-ai-projects/bankshield-ai/`  
References: EGKP + sibling `adviseguard-ai/`.

---

## Purpose

1. Ingest synthetic fraud / AML alerts across payment rails  
2. Gather KYC, transaction, graph, regulatory, and similar-case evidence  
3. Produce an investigator-ready, explainable recommendation  
4. Pause for **HITL** on high-risk paths before drafting a SAR-style package  

The system **never** makes the final high-risk filing decision alone.

UI: FastAPI investigator console on `http://127.0.0.1:8003`.

---

## Locked decisions

| Area | Decision |
|------|----------|
| Orchestration | LangGraph supervisor loop — workers never route to each other |
| Workers | triage_router → identity_kyc → transaction_intel → graph_walker → regulatory_rag → similar_case_retriever → risk_scorer → recommender → grounder_judge → hitl → sar_publisher |
| Models | `BANKSHIELD_MODEL` Bedrock/Vertex/`fake`; cross-provider `BANKSHIELD_JUDGE_MODEL` |
| Vectors | Chroma + BM25 + lexical rerank |
| Graph | Neo4j `:7687` or JSON-seed fallback (`data/kg/mule_ring.json`) |
| HITL | `interrupt` only in `hitl` node |
| Graph budget | ≤ 6 tool calls |
| MVP fraud scope | Broad alert types; **deep** tooling for wire/ACH, sanctions/AML, mule GraphRAG |
| UI | FastAPI investigator console — no React/npm in v1 |
| Out of v1 | Temporal, Kafka production, Cytoscape/Next.js, real LexisNexis/Plaid/Alloy, dark-web feeds, 99.99% HA, FinCEN e-filing |

### Do not regress

1. Workers never call each other.  
2. HITL for `risk_band in {high, critical}` or fraud types in `{wire, sanctions, aml, mule}`.  
3. Recommendation evidence IDs must resolve to `evidence[]`.  
4. Citations must resolve to retrieved corpus / fixture docs.  
5. Injection suite ≥ 95%.  
6. Never auto-file a regulatory SAR without human approval on high-risk cases.

---

## Routing

| Condition | Next |
|-----------|------|
| approval rejected | END |
| triage missing | triage_router |
| needs identity | identity_kyc |
| txn features empty | transaction_intel |
| needs_graph and graph_paths empty | graph_walker |
| reg citations empty | regulatory_rag |
| similar cases empty | similar_case_retriever |
| risk_score is None | risk_scorer |
| recommendation is None | recommender |
| grounding missing / revise | grounder_judge |
| high-risk or low confidence / pending | hitl |
| approved/edited/auto and not published | sar_publisher |

---

## Explainability contract

Every recommendation includes: `evidence_ids`, regulatory refs, `graph_explanation`, `similar_case_ids`, `risk_score` / `risk_band`, `confidence`, reasoning summary.

---

## Success metrics (demo)

| Metric | Target |
|--------|--------|
| Groundedness | ≥ 0.85 |
| Evidence ID resolution | ≥ 90% |
| Injection suite | ≥ 95% |
| High-risk HITL | 100% |
| Graph tool budget | ≤ 6 |

---

## Checklist

- [x] Scaffold under banks-fintech / bankshield-ai  
- [x] Docs + prompts (`AS_BUILT`, `SYSTEM_DESIGN`, `project-prompts`, README)  
- [x] Synthetic data + ingest  
- [x] Multi-agent graph  
- [x] FastAPI investigator UI  
- [x] Evals + injection suite  
- [x] Deploy stubs (AgentCore / Vertex)  
