# AdviseGuard AI — System Design

## Lifecycle

```
Customer query or txn alert → FastAPI → LangGraph supervisor
  → intent → RAG → graph → specialists → compliance → risk → synthesize
  → HITL (if required) → publish log
```

## SessionState

See `app/state.py`: intent flags, specialist drafts, compliance/risk scores, final_response, approval, published.

## Knowledge graph

Nodes: Customer, Account, Product, Goal, Device, Transaction, Merchant, FraudPattern  
Rels: `OWNS`, `TRANSFERRED_TO`, `SUITABLE_FOR`, `SIMILAR_TO`, `SHARES_DEVICE`, `MATCHES_PATTERN`

## Corpus domains

`advice_playbooks`, `products`, `regulations`, `fraud_patterns`, `support_kb`, `market_fixture`

## HITL rules

- Fraud `risk_band` in `{high, critical}`  
- Advice marked `high_stakes` (e.g. retirement / aggressive)  
- Compliance score &lt; 0.6 or grounding &lt; 0.7  
- Soft escalate injection patterns  

## Metrics

| Metric | Target |
|--------|--------|
| Groundedness | ≥ 0.85 |
| Citation coverage | ≥ 90% |
| Injection (50) | ≥ 95% |
| High-risk HITL | 100% |
