# Pairwise regression rubric (EGKP)

Compare answer **A** vs **B** for the same query. Used to **gate model/prompt deploys**.

## Rules
- Choose the better answer for accuracy, groundedness, citations, and safety.
- **Ignore position** — A/B order is randomized; do not prefer the first option.
- Ties are allowed when quality is indistinguishable.
- Prefer the answer with fewer unsupported claims; penalize verbosity without new grounded content.

## Output
```json
{"winner": "A"|"B"|"tie", "rationale": "..."}
```
