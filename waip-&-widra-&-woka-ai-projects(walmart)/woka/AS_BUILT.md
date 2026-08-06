# As-Built — Walmart OmniKnowledge AI (WOKA)

**Package:** `woka` v0.1.0  
**UI:** Knowledge Console at `http://127.0.0.1:8006`  
**Status:** Phase 6 complete — batch ingest, cloud adapters, dual deploy, P95 smoke

---

## Purpose

Enterprise multi-agent knowledge OS over Walmart documents and structured data. A LangGraph supervisor fans work to specialized agents, grounds answers with hybrid GraphRAG + SQL + curated external sources, enforces RBAC/ABAC before retrieval, and publishes citation-backed answers with confidence scores.

---

## Locked decisions

| Area | Decision |
|------|----------|
| Orchestration | LangGraph supervisor + parallel `Send`; agents never peer-route |
| v1 agents | `orchestrator`, `security`, `retrieval`, `document`, `sql`, `internet`, `compliance`, `citation`, `analytics`, `observability` |
| Explicitly deferred | CrewAI, live SharePoint/SAP/ServiceNow, LiteLLM, Airflow/Spark, EKS HA |
| Models | `WOKA_MODEL` Bedrock / Vertex / `fake` + throttle fallback |
| Storage | MinIO, Postgres `:5434`, Weaviate `:8082`, Neo4j optional (JSONL KG fallback) |
| Auth | Mock JWT + RBAC/ABAC filters **before** retrieval |
| Citations | Every factual claim → doc_id / page / section / snippet / confidence |
| Golden path | UC-1 Supply Chain Disruption (hurricane / DC closure) |
| Evals | Groundedness ≥95%, citation ≥95%, hallucination ≤2%, RBAC 0% leak, injection ≥95% |
| Explicitly not v1 | Mutating HITL ServiceNow tickets; live SSO |

### Composer constraints (do not regress)

1. Security filters run before retrieval — never retrieve-then-filter.  
2. Agents only talk to the orchestrator.  
3. Factual claims require citations; SQL numbers prefer structured results.  
4. External sources tagged `source_type=external` and compliance-validated.  
5. Injection suite ≥95% and RBAC leak tests 100% before promote.

---

## Graph flow

```
START → firewall → security_agent
                 → orchestrator (plan)
                 → parallel[retrieval|document|sql|internet]
                 → merge
                 → compliance_agent
                 → citation_agent
                 → analytics_agent (optional)
                 → observability_agent
                 → publish → END
```

---

## Verification checklist

- [x] `/health` returns ok with `WOKA_MODEL=fake` (phase=4)  
- [x] Compose stack up (Postgres 5434, Weaviate 8082, MinIO 9002)  
- [x] Schema + SQL seeds applied  
- [x] Sample docs present under `data/sample_docs/`  
- [x] Golden UC-1 `/chat` returns multi-agent answer with SQL + citations  
- [x] Console UI at `/` + SSE `/chat/stream`  
- [x] Phase 5 eval gates (groundedness / injection / LangSmith hooks)  
- [x] `/audit` `/evaluate` `/feedback` live  
- [x] Phase 6 batch ingest + Pinecone/S3 adapters + deploy smokes + P95 < 5s
