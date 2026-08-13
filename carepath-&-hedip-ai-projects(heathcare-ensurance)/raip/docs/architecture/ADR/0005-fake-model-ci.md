# ADR 0005 — Fake model gateway for CI and demos

## Status

Accepted

## Context

CarePath/HEDIP used `*_MODEL=fake` so goldens and injection evals run without cloud keys.

## Decision

`RAIP_MODEL`, `RAIP_JUDGE_MODEL`, `RAIP_EMBEDDINGS` default to `fake`. Hashed embeddings. Deterministic draft/synthesis heuristics keyed off evidence in the prompt. Bedrock/Vertex via the same gateway. Cross-provider judge when both are configured.

## Consequences

CI has no secrets. Demos are reproducible. Production swap is an env var, not a rewrite.
