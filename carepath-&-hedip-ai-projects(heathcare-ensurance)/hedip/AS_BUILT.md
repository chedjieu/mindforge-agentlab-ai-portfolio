# As-Built — HEDIP (Enterprise Healthcare Decision Intelligence Platform)

**Package:** `hedip` v0.1.0  
**Title:** Enterprise Healthcare Decision Intelligence Platform Using Agentic AI, GraphRAG, and Multi-Agent Reasoning  
**UI:** Command Center at `http://127.0.0.1:8009`

---

## Purpose

Umbrella multi-agent platform for healthcare and insurance decision workflows: prior authorization, claims denial prevention, clinical decision support, care coordination, enterprise knowledge Q&A, fraud/W&A scoring, population health risk, and revenue-cycle coding assist. LangGraph master supervisor + intent router dispatch to domain pipelines sharing hybrid RAG, Neo4j GraphRAG, three memory layers, cross-provider judges, and HITL governance. Dual deploy: Bedrock AgentCore + Vertex AI Agent Engine.

---

## Locked decisions

| Area | Decision |
|------|----------|
| Orchestration | LangGraph master supervisor; workers never peer-route |
| Domains | `prior_auth`, `claims`, `clinical_cds`, `care_coord`, `knowledge`, `fraud`, `pop_health`, `rcm` |
| Depth | Full: PA, Claims, CDS, Knowledge · Thin: Care Coord, Fraud, Pop Health, RCM |
| CarePath | Sibling only — CDS reimplemented inside HEDIP |
| HITL | Required for prior_auth, claims, clinical_cds, fraud (investigate) |
| Models | `HEDIP_MODEL` / `HEDIP_JUDGE_MODEL` (cross-provider); `fake` offline |
| RAG | Hybrid BM25 + dense over shared corpus |
| GraphRAG | Neo4j when `NEO4J_URI` set; else JSONL `data/kg/` |
| Memory | Procedural playbooks + episodic decisions + semantic feedback |
| Port | **8009** |
| Evals | Per-domain goldens; injection ≥95% |
| Explicitly not v1 | Live EHR, real CMS/PBM, Kafka-in-path, HIPAA prod hardening |

### Constraints

1. Workers never call each other — only supervisor / domain routers.  
2. Sensitive domains always HITL before publish.  
3. Citations required for policy/clinical claims.  
4. Injection suite ≥95% before promote.

---

## Graph flow

```
START → firewall → intent_router → master_supervisor
  → domain_{prior_auth|claims|clinical_cds|care_coord|knowledge|fraud|pop_health|rcm}
  → shared_judge → hitl? → publish → END
```

---

## Verification checklist

- [x] `HEDIP_MODEL=fake` smoke across domains  
- [x] Golden cases for PA / Claims / CDS / Knowledge  
- [x] Thin domains return structured outputs  
- [x] Injection suite ≥95%  
- [x] AgentCore + Vertex fake entrypoints  
