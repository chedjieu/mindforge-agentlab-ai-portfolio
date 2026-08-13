# System Design — HEDIP

## Problem

Healthcare providers and payers face fragmented systems across EHR, claims, policies, guidelines, pharmacy, and documents. Prior auth, denial prevention, clinical CDS, care coordination, fraud, and knowledge Q&A all need multi-agent retrieval, GraphRAG reasoning, judges, and HITL — not a simple chatbot.

## Platform approach

One Command Center routes each request to a domain pipeline sharing:

- Hybrid RAG (BM25 + dense + metadata)
- Neo4j GraphRAG (JSONL fallback)
- Procedural / episodic / semantic memory
- Cross-provider LLM-as-judge
- Mandatory HITL on high-risk domains
- Dual-cloud deploy adapters

## Domains

See AS_BUILT.md domain catalog. v1 implements four full pipelines and four thin composite workers.

## Non-goals v1

Live Epic/Cerner FHIR, real CMS APIs, production HIPAA BAA infra, multi-domain fan-out in one request.
