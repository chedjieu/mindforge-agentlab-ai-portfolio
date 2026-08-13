# ADR 0006 — Fewer agents, harder contracts

## Status

Accepted

## Context

The original spec listed 11 named agents. Agents without distinct I/O inflate cost and confuse ownership.

## Decision

LangGraph nodes: firewall, supervisor, retrieval, synthesis, drafting, claim_verification, quality_gates, editorial, publication_gate, hitl.

Regulatory, template, safety, and adversarial checks are **functions inside `quality_gates`**. Document intelligence runs on the ingest worker, not on every draft.

## Consequences

Cheaper, testable, honest in a principal-level review. Editorial cannot override grounding.
