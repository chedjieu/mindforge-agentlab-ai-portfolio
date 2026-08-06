# WAIP Threat Model (summary)

## Assets

Associate PII, payroll data, leave/medical context, policy corpus, audit logs, model prompts.

## Threats & controls

| Threat | Control |
|--------|---------|
| Prompt injection / jailbreak | AI firewall patterns + Bedrock Guardrails; 50-attack suite ≥95% |
| Data exfiltration via prompt | ABAC filters; outbound audit scrub; refuse “dump all salaries” |
| Cross-tenant / cross-country read | Metadata filters on country/state/BU before retrieval |
| Unauthorized ticket creation | Compliance judge + HITL |
| PII in logs | Presidio-style masking hooks; redact in audit writer |
| Model supply risk | Dual cloud; no secrets in prompts |
| Poisoned corpus | Pipeline allowlist + versioned policies + signed publish (design) |

## Trust boundaries

Associate channel → BFF → orchestrator → RAG/tools → enterprise systems (mocked). Every crossing carries ABAC claims and correlation `trace_id`.
