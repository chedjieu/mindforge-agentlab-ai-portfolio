---
doc_id: PB-EDU-ONBOARD-01
tenant_id: shared
reusable_ip: true
vertical: edtech
---

# FERPA-safe student data onboarding playbook

Productized R&P IP for education Velocity Pods.

## Pattern
1. Classify data elements as directory vs education records.
2. Enforce least-privilege SIS reads (Banner/Workday stubs).
3. Tenant-partition episodic memory; never index other institutions.
4. Produce audit pack listing reused components and FERPA controls.

## Guardrails
- No bulk SSN export.
- No cross-tenant student roster joins.
- HITL before production promote when PII retention exceeds policy.
