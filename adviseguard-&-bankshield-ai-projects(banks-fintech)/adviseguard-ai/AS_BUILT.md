# As-Built Planning Document

## Project title

**AdviseGuard AI** — Personalized Financial Advice + Fraud Detection + Customer Support

Package: `adviseguard-ai` v0.1.0  
Location: `10.adviseguard-&-bankshield-ai-projects/adviseguard-ai/`  
References: EGKP + sibling `bankshield-ai/`.

---

## Purpose

1. Personalized investment / planning advice aligned to goals and risk tolerance  
2. Real-time-ish fraud screening on transaction alerts  
3. Grounded customer support answers  

High-stakes advice and high/critical fraud always pause for **HITL**.

UI: FastAPI on `http://127.0.0.1:8004` (`/` customer, `/ops` employee).

---

## Locked decisions

| Area | Decision |
|------|----------|
| Orchestration | LangGraph supervisor loop — workers never route to each other |
| Workers | intent_router → hybrid_retriever → graph_walker → financial_advisor / fraud_detector / customer_support → compliance_judge → risk_judge → synthesizer → hitl → response_publish |
| Models | `ADVISEGUARD_MODEL` Bedrock/Vertex/`fake`; cross-provider `ADVISEGUARD_JUDGE_MODEL` |
| Vectors | Chroma `adviseguard_chunks` + BM25 RRF |
| Graph | Neo4j `:7688` or JSON-seed fallback |
| HITL | `interrupt` only in `hitl_node` |
| Graph budget | ≤ 6 tool calls |
| UI | FastAPI dual console — no React/Angular in v1 |
| Out of v1 | LlamaIndex-primary, TFX, Whisper, Scala/Rust, live market APIs |

### Do not regress

1. Workers never call each other.  
2. No guaranteed-return language in advice.  
3. HITL for high/critical fraud and high-stakes advice.  
4. Citations must resolve to retrieved chunk IDs.  
5. Injection suite 50 attacks ≥ 95%.

---

## Routing

| Condition | Next |
|-----------|------|
| approval rejected | END |
| intent is None | intent_router |
| needs_rag and retrieved_chunks == [] | hybrid_retriever |
| needs_graph and graph_paths == [] | graph_walker |
| run_advisor and advice_draft is None | financial_advisor |
| run_fraud and fraud_finding is None | fraud_detector |
| run_support and support_answer is None | customer_support |
| compliance_score is None | compliance_judge |
| risk_score is None | risk_judge |
| final_response is None | synthesizer |
| approval pending | hitl |
| approved/edited/auto and not published | response_publish |

---

## Checklist

- [x] Scaffold under banks-fintech-systems/adviseguard-ai  
- [x] Docs + prompts  
- [x] Synthetic data + ingest  
- [x] Multi-agent graph  
- [x] FastAPI UI  
- [x] Evals + 50-attack suite  
- [x] Deploy stubs  
