# Retrieval rubric (EGKP)

Judge retrieved chunks for a query. Used to **ship retrieval config changes**.

## Criteria
1. **Relevance** — top chunks address the query intent.
2. **Coverage** — key entities / facts needed to answer appear in the set.
3. **ACL correctness** — no chunk whose `acl_roles` excludes the requester role (unless acl empty).

## Scoring
Return JSON:
```json
{"relevance": 0.0-1.0, "coverage": 0.0-1.0, "acl_ok": true, "score": 0.0-1.0, "feedback": "..."}
```
`score = 0.45*relevance + 0.45*coverage + 0.10*(1 if acl_ok else 0)`.
Pass threshold for ship gate: `score >= 0.70` (configurable).
