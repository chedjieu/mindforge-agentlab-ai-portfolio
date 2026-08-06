# Architecture

Canonical HLA/LLA for R&P Agentic Delivery Fabric. Narrative design: [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md). Locked decisions: [`../AS_BUILT.md`](../AS_BUILT.md).

## High-Level Architecture (HLA)

Adapted from [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) §3.

```mermaid
flowchart LR
  subgraph clients [Clients]
    Cockpit[Delivery_Cockpit]
    SlackHitl[Slack_HITL]
  end
  subgraph runtime [Agent_Runtime]
    FastAPI[FastAPI_8002]
    LG[LangGraph_Supervisor]
  end
  subgraph knowledge [Knowledge_Plane]
    Vec[Tenant_Vector_Index]
    Neo[Neo4j_KG]
    Store[LangGraph_Store]
  end
  subgraph models [Model_Plane]
    Bedrock[AWS_Bedrock]
    Vertex[GCP_Vertex]
    Guards[Bedrock_Guardrails]
  end
  subgraph quality [Quality_Plane]
    LS[LangSmith]
    Judges[LLM_as_Judge]
    RedTeam[Injection_Suite]
  end

  Cockpit --> FastAPI --> LG
  SlackHitl -.-> FastAPI
  LG --> Vec
  LG --> Neo
  LG --> Store
  LG --> Bedrock
  LG --> Vertex
  Guards --> Bedrock
  Judges --> LS
  RedTeam --> LS
```

Workers: `vertical_router` → `compliance_mapper` → `reuse_broker` → `retrieval` → `engagement_synthesizer` → `judge_gate` → `hitl` → `audit_publish`.

## Low-Level Architecture (LLA)

Regulated engagement happy path (e.g. healthcare / finserv) with mandatory HITL before audit publish.

```mermaid
sequenceDiagram
  participant User
  participant API as FastAPI_8002
  participant Sup as Supervisor
  participant VR as VerticalRouter
  participant CM as ComplianceMapper
  participant RB as ReuseBroker
  participant Ret as Retrieval
  participant Syn as EngagementSynthesizer
  participant Judge as JudgeGate
  participant HITL as HITL
  participant Pub as AuditPublish

  User->>API: POST /ingest or /ingest/demo
  API->>Sup: start engagement thread
  Sup->>VR: classify brief
  VR-->>Sup: vertical, sensitivity, policy_pack_id
  Sup->>CM: map regs to guardrails
  CM-->>Sup: guardrail_config
  Sup->>RB: sanitize reusable IP
  RB-->>Sup: reuse_decisions
  Sup->>Ret: tenant-scoped hybrid RAG + Neo4j
  Ret-->>Sup: evidence
  Sup->>Syn: draft engagement plan
  Syn-->>Sup: draft_plan
  Sup->>Judge: compliance / faithfulness / leakage
  Judge-->>Sup: judge_scores pass
  Sup->>HITL: interrupt HITL required
  HITL-->>API: pending card
  User->>API: POST /approve/{thread_id}
  API->>HITL: resume approved
  HITL-->>Sup: approval
  Sup->>Pub: publish audit pack
  Pub-->>Sup: published, audit_pack_id
  Sup-->>API: result
  API-->>User: client-safe plan + provenance
```
