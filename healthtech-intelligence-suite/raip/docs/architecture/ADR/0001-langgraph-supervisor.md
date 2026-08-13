# ADR 0001 — LangGraph supervisor, workers never peer-route

## Status

Accepted

## Context

CarePath/HEDIP showed that peer-routing among workers creates uncontrolled loops and opaque tool use. RAIP has a longer pipeline (retrieve → draft → verify → gates).

## Decision

Use a LangGraph supervisor that is routing-only. Worker nodes return to the supervisor. Hard `max_steps` cap. Supervisor never generates clinical/regulatory text.

## Alternatives

- Fully sequential graph without supervisor: simpler, less flexible for revise loops.
- Multi-agent debate: high cost, weak auditability.

## Consequences

Testable routing table. Loop protection. Same interview story as CarePath, with a stricter evidence pipeline.
