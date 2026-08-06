---
doc_id: RB-OPS-backup
domain: operations
doc_type: runbook
plant: Global
acl_roles: [sre, ops, engineer]
effective_date: 2024-08-01
supersedes: 
entities: [RB-OPS-backup, Svc-payment]
---

# Backup Restore

Restore payment-service Postgres from PITR; validate checksum before cutover.
