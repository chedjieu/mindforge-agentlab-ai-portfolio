# WAIP SLO & Evaluation

## SLOs

| Metric | Target |
|--------|--------|
| Availability | 99.9%+ |
| P95 latency (FAQ/cached) | &lt; 2s |
| P95 latency (multi-agent) | measured; optimize toward &lt; 5s |
| Concurrent design | 100k+ |
| Injection block rate | ≥ 95% |

## Offline metrics

- IR: Recall@K, Precision@K, MRR, nDCG  
- LLM: groundedness, faithfulness, hallucination rate, toxicity, citation accuracy  

## Online metrics

User satisfaction, task completion, e2e latency, cost/request, first-contact resolution.

## Gates

1. `evals/run_all.py` — e2e golden + groundedness smoke  
2. `security/injection_eval.py` — 50 attacks ≥95%  
3. LangSmith experiments (when `LANGCHAIN_API_KEY` set) must meet judge floors before AgentCore/Vertex promote  
