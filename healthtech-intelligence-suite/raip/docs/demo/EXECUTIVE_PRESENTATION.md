# Executive presentation — RAIP

## Business problem

Clinical and regulatory authors must draft sections that can survive review. Generic generative AI produces fluent text that may not be grounded in the organization’s approved sources.

## Risk

Unsupported medical or regulatory claims, silent use of superseded guidelines, citation hallucination, and prompt injection hidden in PDFs.

## Solution

RAIP is an evidence-first agentic platform: ingest versioned sources, retrieve with hybrid search and GraphRAG supersession, draft only from evidence, decompose into claims, verify each claim, gate publication, and require a human.

## Differentiator vs CarePath/HEDIP

Those systems retrieve and cite. RAIP adds **claim-level support status**, **authority tiers**, **version supersession**, and **boolean publication gates** that a 97% score cannot bypass.

## Agent workflow

Supervisor routes; workers never peer-call. Retrieval → synthesis → draft → verify → gates → HITL.

## Technology choices

LangGraph, FastAPI, SQLite/Postgres, BM25+dense RRF, optional Neo4j, fake/Bedrock/Vertex gateway. Fewer agents, harder contracts.

## Security

Untrusted documents, injection suite ≥95% target, tenant isolation, RBAC roles, audit.

## Evaluation

Deterministic goldens + injection eval. LLM-as-judge is secondary.

## Pilot → scale

One document type, synthetic corpus, mandatory HITL, measured grounding and edit rate → more templates/tenants → multi-region, IdP, OCR, pgvector/OpenSearch.

## Business value

Productivity with defensible drafts; lower hallucination and outdated-reference risk; reviewer time spent on conflicts, not first-pass wording.

## Limitations

Not a diagnostic device. Not HIPAA certified. OCR and malware scanning are boundaries. Lexical entailment is v1, not clinical-grade NLI.

## Roadmap

NLI entailment model, production OCR, OIDC, managed vector DB, cost-based model routing, additional document types.
