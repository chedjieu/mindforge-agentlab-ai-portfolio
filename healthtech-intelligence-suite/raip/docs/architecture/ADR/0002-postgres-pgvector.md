# ADR 0002 — Postgres as system of record; pgvector as production vector path

## Status

Accepted

## Context

CarePath stored corpus files and optional Chroma. RAIP needs versioned documents, tenant isolation, audit, and claim–evidence FKs.

## Decision

- **Local default:** SQLite + JSON embeddings + in-process cosine (no Docker required for tests).
- **Local Docker:** Postgres (`pgvector/pgvector`) as the production-shaped store.
- **Production:** same schema; optional Pinecone/OpenSearch behind `VectorStore` adapter.

Postgres remains source of truth for text, versions, drafts, reviews, and audit. Vector search is an index, not a system of record.

## Alternatives

- Pinecone-only: poor local DX, weak FK integrity.
- FAISS-only: no tenancy, no durability for the evidence store.

## Consequences

One metadata model. Tests run offline. Documented migration: swap the vector adapter, keep chunk IDs.
