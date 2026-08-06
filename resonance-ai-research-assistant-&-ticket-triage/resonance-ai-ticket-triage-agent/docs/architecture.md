# Architecture

Canonical HLA/LLA for the Resonance Ticket Triage Agent. There is no standalone `SYSTEM_DESIGN.md` in this package; HLA is extracted from the README Mermaid / ASCII flow. Locked decisions: [`../AS_BUILT.md`](../AS_BUILT.md).

## High-Level Architecture (HLA)

```mermaid
flowchart TD
  START[START] --> Sup[supervisor]
  Sup -->|classify| Triager[triager]
  Triager --> Sup
  Sup -->|investigate| Investigator[investigator]
  Investigator --> Sup
  Sup -->|draft| Responder[responder]
  Responder --> Sup
  Sup -->|approve| HITL[hitl]
  HITL --> Sup
  Sup -->|dispatch| Send[send]
  Send --> Sup
  Sup -->|done_or_rejected| END[END]
```

| Worker | Role |
|--------|------|
| `triager` | Category + severity |
| `investigator` | Logs / metrics / runbooks / history (≤ 8 tools) |
| `responder` | Draft reply using three memory layers |
| `hitl` | Interrupt → approve \| edit \| reject |
| `send` | Mock email (+ Slack if P1) |

UI: FastAPI approval console on port **8002**.

## Low-Level Architecture (LLA)

Happy path: demo ticket → investigate → draft → HITL approve → send.

```mermaid
sequenceDiagram
  participant User
  participant API as FastAPI_8002
  participant Sup as Supervisor
  participant Tri as Triager
  participant Inv as Investigator
  participant Resp as Responder
  participant HITL as HITL
  participant Send as Send

  User->>API: POST /ingest or /ingest/demo
  API->>Sup: start ticket thread
  Sup->>Tri: classify ticket
  Tri-->>Sup: category, severity
  Sup->>Inv: investigate with tools
  Inv-->>Sup: findings
  Sup->>Resp: draft customer reply
  Resp-->>Sup: draft + escalate_or_send
  Sup->>HITL: interrupt pending approval
  HITL-->>API: pending card
  User->>API: POST /approve/{thread_id}
  API->>HITL: resume approved
  HITL-->>Sup: approval
  Sup->>Send: mock dispatch
  opt severity_P1
    Send->>Send: Slack hash_incidents
  end
  Send-->>Sup: sent
  Sup-->>API: done
  API-->>User: resolution status
```
