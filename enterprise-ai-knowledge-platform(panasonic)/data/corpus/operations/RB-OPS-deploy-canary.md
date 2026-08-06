---
doc_id: RB-OPS-canary
domain: operations
doc_type: runbook
plant: Global
acl_roles: [sre, ops, engineer]
effective_date: 2024-10-01
supersedes: 
entities: [RB-OPS-canary]
---

# Canary Deploy

Start at 5% traffic for 20 minutes; abort on p95 > 2× baseline.
