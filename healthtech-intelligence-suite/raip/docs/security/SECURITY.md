# Security

**No production PHI. No HIPAA certification claim.** This document describes HIPAA-ready *patterns*.

## Threat model (STRIDE)

| Threat | Example | Mitigation |
|--------|---------|------------|
| Spoofing | Fake reviewer | Header RBAC locally; OIDC in production; audit actor_id |
| Tampering | Citation swap / poisoned PDF | Checksums, untrusted wrappers, citation validation vs chunk ids |
| Repudiation | “I never approved that” | AuditEvent + review rows |
| Information disclosure | Cross-tenant retrieval | `tenant_id` on every query; isolation tests |
| Denial of service | Huge PDF / agent loop | Size limit, `max_graph_steps` |
| Elevation of privilege | Prompt injection to auto-approve | Publication gate ignores model; HITL required |

## Prompt injection

Source documents are data. `scan_text` flags patterns; `wrap_untrusted` delimits retrieved text; user jailbreaks can hard-block. Target: **≥95%** on 50 attacks (`python -m security.injection_eval`).

## Tenant isolation

All tables include `tenant_id`. Retrieval and graph edges are tenant-scoped. CI test: Northstar cannot see `SECRET TOKEN` from `tenant-other`.

## RBAC

Roles: AUTHOR, MEDICAL_REVIEWER, REGULATORY_REVIEWER, QUALITY_REVIEWER, ADMIN, AUDITOR. Local headers: `X-Tenant-Id`, `X-User-Id`, `X-Role`.

## Uploads

Allowlisted extensions, size cap, SHA-256. Malware scan is a **boundary** — ClamAV is production, not v1.

## Secrets and encryption

No hardcoded cloud keys. TLS in production. SQLite/Postgres encryption at rest is a platform control, not implemented in-app.

## PII

Synthetic data. Redaction regex in logs. Do not log full clinical drafts at info level in production configurations.
