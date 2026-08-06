# WOKA System Design

## Problem

Walmart knowledge spans merchandising, supply chain, stores, HR, finance, compliance, pharmacy, and ecommerce — fragmented across PDFs, SharePoint, Confluence, Jira, ServiceNow, ERP, Snowflake, and external regulators. Associates lose hours searching; wrong answers cause inventory loss, fines, recalls, and OSHA/pharmacy failures.

## Solution

WOKA is a multi-agent RAG knowledge engine that:

1. Ingests and classifies enterprise documents with rich metadata.  
2. Retrieves via hybrid vector + BM25 + metadata + graph (+ SQL + internet).  
3. Enforces RBAC/ABAC **before** any content reaches the LLM.  
4. Coordinates specialized agents under a LangGraph supervisor.  
5. Publishes cited answers with confidence and full audit trail.  
6. Gates quality with LLM-as-judge (groundedness, citations, hallucination).

## Use-case matrix

| UC | Priority | Example | Success |
|----|----------|---------|---------|
| UC-1 Supply chain disruption | P0 | Hurricane closes SE DCs | Suppliers, delays, inventory ≤300mi, alt contracts, 48h stockouts — cited |
| UC-2 Associate knowledge | P1 | Hazardous waste / CA payroll policy | Correct policy + region scope |
| UC-3 Product recall | P2 | FDA contamination | SKUs, warehouses, contracts, action plan |
| UC-4 Merchandising | P3 | TV sales decline Region 7 | Correlated pricing/inventory (scaffold) |
| UC-5 Exec risk | P3 | Major operational risks | Multi-source summary (scaffold) |
| UC-6 Injection | — | Jailbreak / dump docs | Firewall blocks; audit |

## Metadata schema (chunk)

`doc_id`, `department`, `bu`, `store`, `region`, `country`, `page`, `section`, `heading`, `table_id`, `sku`, `supplier`, `category`, `confidentiality`, `role`, `version`, `effective_date`, `expiration_date`, `language`, `keywords`, `entity_ids`

## ACL model

```
User → Role(s) → Permissions
Document/Chunk → Policy → Rules(role, dept, region, clearance)
```

Retrieval always scoped:

```
WHERE acl_policy IN user.allowed_policies
  AND region IN user.regions
  AND confidentiality <= user.clearance
```

## Hybrid retrieval

```
Query → rewrite → (vector + BM25 + metadata + KG + SQL + internet)
      → rank fusion → cross-encoder rerank → top context → LLM
```

## Eval gates

| Gate | Target |
|------|--------|
| Groundedness | ≥ 95% |
| Citation accuracy | ≥ 95% |
| Hallucination rate | ≤ 2% |
| Retrieval precision@K | ≥ 90% |
| RBAC leak rate | 0% |
| Injection block | ≥ 95% |
| P95 answer latency | < 5s (sample corpus) |

## Non-goals (v1)

Live SSO, live ERP/SharePoint connectors, autonomous ServiceNow writes, multi-region HA, voice, digital twin.
