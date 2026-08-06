---
doc_id: RB-OPS-kafka
domain: operations
doc_type: runbook
plant: Global
acl_roles: [sre, ops, engineer]
effective_date: 2025-04-01
supersedes: 
entities: [RB-OPS-kafka, Svc-events]
---

# Kafka Consumer Lag

If Svc-events lag > 100k, scale consumers and pause non-critical producers.
