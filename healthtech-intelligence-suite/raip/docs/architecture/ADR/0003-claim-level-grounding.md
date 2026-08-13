# ADR 0003 — Claim-level grounding is deterministic-first

## Status

Accepted

## Context

LLM-as-judge can give a high score while a material claim is unsupported. That is the CarePath/HEDIP gap.

## Decision

After drafting:

1. Split material claims (deterministic sentence segmentation + classifiers).
2. Match each claim to retrieved chunks (lexical Jaccard + embedding cosine).
3. Assign `SUPPORTED | PARTIALLY_SUPPORTED | UNSUPPORTED | CONTRADICTED | NOT_APPLICABLE`.
4. LLM judge is **secondary** and cannot override a critical unsupported/contradicted material claim.

Unsupported material claims block publication.

## Alternatives

- Trust generator citations: citation hallucination risk.
- NLI model for entailment: better accuracy, extra dependency; future enhancement.

## Consequences

Evals are reproducible with `fake`. Interview answer: "generation is subordinate to evidence."
