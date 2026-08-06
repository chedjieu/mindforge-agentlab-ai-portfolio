# As-Built — Walmart Associate Intelligence Platform (WAIP)

**Package:** `waip` v0.1.0  
**UI:** Associate Console at `http://127.0.0.1:8004`

---

## Purpose

Mission-critical multi-agent enterprise assistant for 2M+ Walmart associates. A LangGraph **master orchestrator** fans work out in **parallel** to domain specialists (HR, Payroll, Benefits, Leave, Ticket, Search), grounds answers with hybrid GraphRAG (BM25 + vectors + Neo4j), runs Compliance + Response Validator judges, and executes HITL-gated actions against mocked Workday / ServiceNow systems. Dual deploy: **Bedrock AgentCore** and **Vertex AI Agent Engine**.

---

## Locked decisions

| Area | Decision |
|------|----------|
| Orchestration | LangGraph master planner + parallel `Send` fan-out; workers never peer-route |
| Workers | `hr`, `payroll`, `benefits`, `leave`, `ticket`, `search` (subset per intent) |
| Judges | `compliance_agent`, `response_validator` (LLM ∩ heuristics) before publish/action |
| HITL | `interrupt` required for mutating actions (create ticket, submit leave) |
| Chat models | Bedrock primary / Vertex swap via `WAIP_MODEL`; `fake` for offline/CI |
| Embeddings | Titan / Vertex / fake hashed vectors |
| Vector / hybrid | Local hybrid (BM25-style + dense) over `data/corpus`; Weaviate/Pinecone in compose profile |
| GraphRAG | Neo4j when `NEO4J_URI` set; else JSONL seeds in `data/kg/` |
| Memory | Procedural playbooks + episodic JSONL + semantic store |
| Tools | MCP-shaped mocks: Workday, ServiceNow, Leave, SAP |
| Checkpointer | Sqlite local → `checkpoints.sqlite`; Postgres via `POSTGRES_DSN` |
| Deploy | `deploy/agentcore` + `deploy/vertex_engine` |
| Evals | LangSmith-ready; injection suite **≥ 95%** on 50 attacks |
| UI | FastAPI + streaming console (Next.js production path documented) |
| Explicitly not v1 hot path | AutoGen swarm, Kafka-in-request-path, live Workday/ServiceNow |

### Composer constraints (do not regress)

1. Workers never call each other — only master routes / fans out.  
2. Every retrieval and tool call is scoped by ABAC (country, state, store, role, BU).  
3. Mutating actions require Compliance pass + HITL approval.  
4. Factual claims require citations from retrieved evidence.  
5. Injection suite must stay ≥95% before deploy promote.

---

## Graph flow

```
START → firewall → master_planner
                 → parallel[hr|payroll|benefits|leave|ticket|search]
                 → aggregator
                 → response_validator
                 → compliance_agent
                 → hitl (if action)
                 → action_executor
                 → publish → END
```

---

## Verification checklist

- [ ] `WAIP_MODEL=fake` e2e golden paycheck/leave path produces citations + proposed ticket  
- [ ] HITL approve creates mock ServiceNow `INC*`  
- [ ] ABAC filters exclude out-of-country policy chunks  
- [ ] `python -m evals.run_all` passes  
- [ ] `python -m security.injection_eval` ≥ 95%  
- [ ] AgentCore + Vertex entrypoints import and run fake smoke  
