# ADR 0008 — Publication is a boolean gate, not a score

## Status

Accepted

## Context

A 97% quality score with one unsupported dosage claim must not publish.

## Decision

```
APPROVED iff
  grounding PASS
  AND citation PASS
  AND safety PASS
  AND regulatory PASS
  AND template PASS
  AND security PASS
  AND human approval
```

Critical safety failure ⇒ `PUBLICATION_BLOCKED` regardless of weighted score. Weights are configurable and documented.

## Consequences

The demo can show "high score, still blocked." That is the enterprise differentiator.
