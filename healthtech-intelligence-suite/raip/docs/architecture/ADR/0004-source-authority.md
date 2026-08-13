# ADR 0004 — Configurable source authority and supersession

## Status

Accepted

## Context

Not all PDFs are equal. Conflicting guidelines must not be silently merged.

## Decision

Authority tiers 1–6 (regulatory → unverified). Document versions carry `effective_date` and `supersedes_version_id`.

Conflict policy:

- If v2 supersedes v1, prefer v2; do not treat v1 as an equal contradiction.
- If two current sources conflict, surface `CONTRADICTORY_EVIDENCE` and require HITL.
- Never silently pick a source for a material conflict.

## Alternatives

- Recency-only: ignores regulatory hierarchy.
- LLM arbitration: not auditable.

## Consequences

GraphRAG (`DOCUMENT_SUPERSEDES_DOCUMENT`) is justified. Postgres still stores the FK so Neo4j is optional.
