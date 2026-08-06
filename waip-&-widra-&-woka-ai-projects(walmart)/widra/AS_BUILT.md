# As-Built — Walmart Intelligent Document Retrieval Assistant (WIDRA)

**Package:** `widra` v0.1.0 (planned)  
**UI:** Document Console at `http://127.0.0.1:8005` (planned)  
**Status:** Phase 2 — ingestion pipeline (parse → chunk → embed → index)

---

## Purpose

Secure, scalable RAG assistant over 5,000+ Walmart PDF documents. Employees ask natural-language questions; the system retrieves authorized chunks, generates cited answers, and returns deterministic figures for tables and numeric facts.

---

## Locked decisions

| Area | Decision |
|------|----------|
| Orchestration | LangGraph supervisor routes to 5 agents; agents do not call each other directly |
| Agents | `ingestion`, `retrieval`, `answer`, `auth`, `observability` |
| PDF parsing | Unstructured or Docling for text + tables; OCR fallback for scanned pages |
| Chunking | Semantic (heading/section aware), 400–600 tokens, 80-token overlap; table rows kept atomic |
| Embeddings | Titan / Vertex / fake; one model per environment, versioned in metadata |
| Vector store | Weaviate (local dev) / Pinecone (prod); namespace per environment |
| Metadata DB | PostgreSQL — document registry, ACL, ingestion status, chunk lineage |
| Object store | S3 (prod) / MinIO (local) — immutable source PDFs keyed by `doc_id` |
| Retrieval | Hybrid BM25 + dense + metadata pre-filter → cross-encoder rerank → top-k |
| Auth | RBAC + optional ABAC (dept, region, clearance); filters applied **before** vector search |
| Answer policy | All factual claims require citations; numeric answers prefer extracted table cells |
| Models | `WIDRA_MODEL` gateway: Bedrock primary, Vertex swap, `fake` for offline/CI |
| Evals | Retrieval recall@k, answer groundedness, citation coverage, RBAC leak tests |
| Explicitly not v1 | Live SSO integration, multi-region HA, real-time PDF watch (batch + manual re-ingest only) |

### Composer constraints (do not regress)

1. Auth filters run at retrieval time — never retrieve-then-filter.  
2. Every factual claim in an answer must cite a chunk with `doc_id`, page, and snippet.  
3. Table/numeric answers must trace to extracted cell values when available.  
4. Source PDFs are immutable; re-ingest creates a new version, never overwrites.  
5. RBAC leak tests must pass 100% before deploy promote.

---

## Agent graph flow

```
START → auth_agent (resolve user + ACL scope)
      → retrieval_agent (hybrid search within scope)
      → answer_agent (grounded generation + table fact lookup)
      → observability_agent (trace + metrics emit)
      → publish → END

Ingestion (async, separate graph):
upload → parse → chunk → embed → index → register metadata → END
```

---

## Verification checklist (pre-launch)

- [ ] Ingest 50 sample PDFs (text + table heavy) without error  
- [ ] Hybrid retrieval beats BM25-only on eval set (recall@5 ≥ 0.80)  
- [ ] Answers include citations for 100% of factual claims on golden set  
- [ ] RBAC tests: restricted user gets zero out-of-scope chunks  
- [ ] Table query returns exact cell value matching source PDF  
- [ ] `WIDRA_MODEL=fake` e2e smoke passes offline  
- [ ] Injection suite ≥ 95% on 50 attacks  
