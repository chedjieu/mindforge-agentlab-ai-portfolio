# ADR 0007 — GraphRAG for version, authority, and claim–evidence edges

## Status

Accepted

## Context

Vector search cannot express "v2 supersedes v1" or "claim C is contradicted by chunk X."

## Decision

Neo4j when `NEO4J_URI` is set. Otherwise an in-memory/JSONL graph with the same relationship types. Postgres remains source of truth.

Relationships: `DOCUMENT_SUPERSEDES_DOCUMENT`, `SECTION_CONTAINS_CHUNK`, `CLAIM_SUPPORTED_BY`, `CLAIM_CONTRADICTED_BY`.

## Alternatives

- SQL recursive CTEs only: workable but weaker neighborhood expansion for GraphRAG demos.
- Neo4j as the only store: operationally heavier locally.

## Consequences

Graph is not decorative. Fallback keeps CI green without Neo4j.
