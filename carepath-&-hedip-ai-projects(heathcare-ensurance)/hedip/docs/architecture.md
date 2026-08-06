# Architecture

Canonical HLA/LLA for HEDIP (Healthcare Decision Intelligence Platform). Mirrors the CarePath HLA pattern (console → FastAPI → LangGraph → knowledge + model planes) with multi-domain routing. Narrative: [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md). Locked decisions: [`../AS_BUILT.md`](../AS_BUILT.md).

**Port:** Command Center FastAPI **8009**.

## High-Level Architecture (HLA)

```mermaid
flowchart LR
  subgraph clients [Clients]
    CC[CommandCenter]
  end
  subgraph runtime [AgentRuntime]
    FastAPI[FastAPI_8009]
    FW[Firewall]
    IR[IntentRouter]
    Sup[MasterSupervisor]
    Domains[DomainPipelines]
  end
  subgraph knowledge [KnowledgePlane]
    Vec[Hybrid_RAG]
    Neo[Neo4j_KG]
    Mem[Three_Memory_Layers]
  end
  subgraph models [ModelPlane]
    Bedrock[AWS_Bedrock]
    Vertex[GCP_Vertex]
    Judges[LLM_as_Judge]
  end

  CC --> FastAPI --> FW --> IR --> Sup --> Domains
  Domains --> Vec
  Domains --> Neo
  Domains --> Mem
  Domains --> Bedrock
  Domains --> Vertex
  Domains --> Judges
```

Domains (v1): `prior_auth`, `claims`, `clinical_cds`, `care_coord`, `knowledge`, `fraud`, `pop_health`, `rcm`. HITL required for prior_auth, claims, clinical_cds, and fraud (investigate).

Flow: `START → firewall → intent_router → master_supervisor → domain_* → judge → HITL → publish`.

## Low-Level Architecture (LLA)

Happy path: prior-authorization request with HITL before publish.

```mermaid
sequenceDiagram
  participant User
  participant API as FastAPI_8009
  participant FW as Firewall
  participant IR as IntentRouter
  participant Sup as MasterSupervisor
  participant Dom as Domain_PriorAuth
  participant RAG as HybridRAG_KG
  participant Judge as JudgeGate
  participant HITL as HITL
  participant Pub as Publish

  User->>API: submit prior_auth case
  API->>FW: scan input
  FW-->>API: allow
  API->>IR: classify intent
  IR-->>API: domain_prior_auth
  API->>Sup: dispatch domain pipeline
  Sup->>Dom: run prior_auth workers
  Dom->>RAG: retrieve policies + guidelines
  RAG-->>Dom: evidence
  Dom-->>Sup: draft recommendation
  Sup->>Judge: safety + policy scores
  Judge-->>Sup: pass
  Sup->>HITL: interrupt HITL required
  HITL-->>API: pending card
  User->>API: approve
  API->>HITL: resume
  HITL-->>Sup: approval
  Sup->>Pub: publish decision + audit
  Pub-->>Sup: published
  Sup-->>API: result
  API-->>User: cited prior_auth outcome
```
