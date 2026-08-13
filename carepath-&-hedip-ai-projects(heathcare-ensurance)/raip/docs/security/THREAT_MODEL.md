# Threat model — RAIP

Actors: Author, Reviewer, Auditor, Attacker (prompt injection, poisoned PDF, cross-tenant).

Assets: Source PDFs, evidence chunks, drafts, claims, audit log, model prompts, tenant isolation.

Trust zones: Browser → API → workers → data stores → model providers.

See STRIDE table in [SECURITY.md](SECURITY.md).
