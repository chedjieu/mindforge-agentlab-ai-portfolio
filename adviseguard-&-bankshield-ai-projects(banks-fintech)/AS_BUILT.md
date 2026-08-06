# As-Built — AdviseGuard AI & BankShield AI Workspace

**Workspace:** AdviseGuard AI + BankShield AI (banks / fintech agentic platforms)  
**Packages:** `adviseguard-ai` v0.1.0 · `bankshield-ai` v0.1.0  
**UIs:** BankShield investigator console `8003` · AdviseGuard dual console `8004`

Per-project detail: [adviseguard-ai/AS_BUILT.md](adviseguard-ai/AS_BUILT.md) · [bankshield-ai/AS_BUILT.md](bankshield-ai/AS_BUILT.md).

---

## Purpose

This workspace holds two sibling interview-grade / portfolio systems that share the same platform stack (LangGraph orchestration, hybrid RAG, Neo4j GraphRAG, memory, judges, HITL, dual-cloud deploy stubs) but different product scopes:

| System | Scope |
|--------|--------|
| **BankShield AI** | Multi-agent financial-crime investigation: alert → evidence → risk → recommendation → HITL → SAR draft |
| **AdviseGuard AI** | Personalized investment advice + transaction fraud screening + grounded customer support |

---

## Locked workspace decisions

| Area | Decision |
|------|----------|
| Relationship | **Siblings** — neither package imports or calls the other |
| Orchestration | LangGraph supervisors; workers never peer-route |
| Ports | BankShield **8003** · AdviseGuard **8004** |
| Neo4j / Postgres | BankShield `:7687` / `:5434` · AdviseGuard `:7688` / `:5435` |
| Env prefixes | `BANKSHIELD_*` vs `ADVISEGUARD_*` (no shared env namespace) |
| Offline / CI | `*_MODEL=fake` on both |
| Judges | Cross-provider when both Bedrock and Vertex are configured |
| RAG | Hybrid BM25 + dense; Neo4j when available, else JSON KG seeds |
| UI | FastAPI consoles — no React/npm in v1 |
| Deploy | AgentCore + Vertex stubs in each package |
| Safety bar | Injection suite **≥ 95%** before promote |
| Explicitly not v1 | Live market/KYC vendors, Kafka production, Next.js/Cytoscape, 99.99% HA |

### Constraints (do not regress)

1. Workers never call each other — only supervisors route.  
2. High-risk / high-stakes decisions always require HITL before publish.  
3. Citations and evidence IDs must resolve to retrieved or gathered artifacts.  
4. Packages stay runtime-decoupled.  
5. Injection suites stay ≥95% on both packages before deploy promote.  
6. AdviseGuard never uses guaranteed-return language in advice.

---

## Platform stack (shared pattern)

```
UI (FastAPI console)
  → supervisor / intent router
  → domain or worker agents
  → hybrid RAG + GraphRAG tools
  → LLM-as-judge (cross-provider)
  → HITL interrupt (sensitive paths)
  → publish / audit log
```

| Layer | Tech |
|-------|------|
| Orchestration | LangGraph |
| Models | Bedrock / Vertex / `fake` via gateway env vars |
| RAG | Chroma + BM25 over `data/corpus` |
| GraphRAG | Neo4j or `data/kg/` JSON seeds |
| Checkpointer | Sqlite local; Postgres optional |
| Evals | Golden / e2e + `security/injection_eval` |
| Infra | `docker-compose.yml` per package |

---

## BankShield AI (summary)

**Flow:** triage → identity → transaction → graph → regulatory RAG → similar cases → risk → recommender → grounder → HITL → SAR publish.

**Deep tooling:** wire/ACH, sanctions/AML, mule-network GraphRAG.  
**Shallow:** card, ATO, APP/BEC, FedNow/RTP (same pipeline, thinner tools).

**HITL:** `risk_band in {high, critical}` or fraud types in `{wire, sanctions, aml, mule}`.

---

## AdviseGuard AI (summary)

**Flow:** intent → hybrid retriever → graph walker → advisor / fraud / support → compliance → risk → synthesizer → HITL → publish.

**HITL:** high/critical fraud, high-stakes advice, low compliance/grounding scores.

---

## Workspace verification checklist

- [x] Root `README.md`, `AS_BUILT.md`, and `.cursor/plan.md` present  
- [x] Each package has its own README, AS_BUILT, SYSTEM_DESIGN, project-prompts  
- [x] Ports do not collide (8003 / 8004; Neo4j 7687 / 7688; Postgres 5434 / 5435)  
- [x] Env prefixes isolated (`BANKSHIELD_*` / `ADVISEGUARD_*`)  
- [x] No runtime coupling between packages  
- [x] Both packages document fake offline e2e + injection ≥95% gates  

---

## Doc map

| Doc | Location |
|-----|----------|
| Workspace README | [README.md](README.md) |
| Workspace as-built | this file |
| Cursor plan | [.cursor/plan.md](.cursor/plan.md) |
| BankShield README / as-built | [bankshield-ai/README.md](bankshield-ai/README.md), [bankshield-ai/AS_BUILT.md](bankshield-ai/AS_BUILT.md) |
| BankShield design | [bankshield-ai/docs/SYSTEM_DESIGN.md](bankshield-ai/docs/SYSTEM_DESIGN.md) |
| AdviseGuard README / as-built | [adviseguard-ai/README.md](adviseguard-ai/README.md), [adviseguard-ai/AS_BUILT.md](adviseguard-ai/AS_BUILT.md) |
| AdviseGuard design | [adviseguard-ai/docs/SYSTEM_DESIGN.md](adviseguard-ai/docs/SYSTEM_DESIGN.md) |
