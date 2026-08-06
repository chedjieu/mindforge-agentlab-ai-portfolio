# WAIP System Design

## Problem

Walmart employs 2M+ associates across countries, stores, FCs, pharmacies, and corporate. HR/payroll/leave/benefits/ticket knowledge is fragmented across Workday, ServiceNow, Confluence, SharePoint, SAP, PDFs, and country policies. Associates lose time navigating systems.

## Solution

WAIP is a generative multi-agent platform:

1. Master orchestrator (LangGraph) interprets multi-intent queries.  
2. Domain workers run **in parallel** with independent retrieval and tools.  
3. Hybrid GraphRAG grounds every factual claim.  
4. Compliance + Response Validator judges enforce RAI and citations.  
5. HITL gates mutating enterprise actions.  
6. Dual-cloud deploy (Bedrock AgentCore + Vertex Agent Engine).

## Use-case matrix

| UC | Intents | Workers | Action |
|----|---------|---------|--------|
| UC-1 Pay short + medical leave | payroll, leave, hr, ticket | parallel 4 | optional ServiceNow |
| UC-2 Benefits eligibility | benefits, hr | parallel 2 | none |
| UC-3 PTO / FMLA balance | leave, hr | parallel 2 | none / leave submit |
| UC-4 Policy Q&A | hr, search | parallel 2 | none |
| UC-5 Injection / jailbreak | — | firewall refuse | none |

## Knowledge graph schema

```
(:Associate)-[:WORKS_AT]->(:Store)
(:Associate)-[:HAS_ROLE]->(:Role)
(:Role)-[:ELIGIBLE_FOR]->(:BenefitsPlan)
(:BenefitsPlan)-[:GOVERNED_BY]->(:Policy)
(:Associate)-[:SUBJECT_TO]->(:LeaveRule)
(:Policy)-[:VERSION]->(:PolicyVersion)
(:LeaveRule)-[:REFERENCES]->(:Policy)
```

## Retrieval

Query → rewriter → hybrid (BM25 + vector + KG hops) → cross-encoder rerank → context builder (ABAC filters applied pre-query).

Semantic chunking: heading/section aligned, 300–500 tokens, 50–100 overlap.

## Judges

| Judge | Floor | Fail behavior |
|-------|-------|---------------|
| Groundedness | 0.85 | clarify / escalate |
| Citation coverage | 0.90 | regenerate or refuse factual claims |
| Compliance / PII | 0.90 | block action; mask |
| Action risk | HITL if mutate | interrupt until approve/reject |

## Memory

- **Procedural:** `data/playbooks/*.yaml`  
- **Semantic:** corpus + KG  
- **Episodic:** `data/episodic/*.jsonl` scoped by associate_id  

## Risks

| Risk | Mitigation |
|------|------------|
| Hallucinated pay/eligibility | citations + confidence floor + no invent |
| Cross-country leakage | ABAC metadata filters |
| Unsafe ticket spam | Compliance + HITL |
| Prompt injection | firewall + 50-attack gate ≥95% |
| Cloud lock-in | dual Bedrock/Vertex gateway |

## Non-goals (v0.1)

Live Workday/ServiceNow, Kafka in request path, full multi-region HA implementation (documented only).
