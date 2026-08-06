# Architecture

Canonical HLA/LLA for WAIP (Walmart Associate Intelligence Platform). Extended layer notes and deploy detail historically lived in uppercase `ARCHITECTURE.md`; this file is the Wave-1 canonical view. See also [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) and [`../AS_BUILT.md`](../AS_BUILT.md).

**Port:** FastAPI BFF **8004**.

## High-Level Architecture (HLA)

ASCII layers converted to Mermaid:

```mermaid
flowchart TB
  subgraph channels [Channels]
    Web[Web]
    Mobile[Mobile]
    Teams[Teams]
  end
  subgraph edge [Edge]
    GW[API_Gateway_WAF]
    Id[SSO_MFA_RBAC_ABAC]
    FW[AI_Firewall_Guardrails]
  end
  subgraph runtime [Runtime]
    BFF[FastAPI_BFF_8004]
    Orch[LangGraph_Master]
    Workers[Parallel_Domain_Workers]
    GraphRAG[Hybrid_GraphRAG]
    MCP[MCP_Tool_Adapters]
    Mem[Three_Layer_Memory]
    Judges[Judges_HITL_Actions]
  end
  subgraph models [Model_Gateway]
    Bedrock[Bedrock]
    Vertex[Vertex]
    Fake[fake]
  end
  Audit[Audit_Compliance_Logs]

  Web --> GW
  Mobile --> GW
  Teams --> GW
  GW --> Id --> FW --> BFF --> Orch
  Orch --> Workers
  Orch --> GraphRAG
  Orch --> MCP
  Orch --> Mem
  Orch --> Judges
  Orch --> Bedrock
  Orch --> Vertex
  Orch --> Fake
  Judges --> Audit
```

Master planner emits parallel `Send(worker, state_slice)` for selected domains (HR / Payroll / Benefits / Leave / Ticket / Search). Aggregator merges evidence; Validator + Compliance run on the merge; mutating actions require HITL then MCP write adapters.

## Low-Level Architecture (LLA)

Happy path: associate query that needs a HITL-gated ServiceNow ticket (e.g. short paycheck + medical leave).

```mermaid
sequenceDiagram
  participant User
  participant API as FastAPI_8004
  participant Orch as MasterOrchestrator
  participant Workers as DomainWorkers
  participant RAG as HybridGraphRAG
  participant Val as ValidatorCompliance
  participant HITL as HITL
  participant MCP as MCP_Adapters
  participant LLM as ModelGateway

  User->>API: POST query SSE
  API->>Orch: start associate thread
  Orch->>LLM: plan domains
  Orch->>Workers: parallel Send slices
  Workers->>RAG: retrieve evidence
  RAG-->>Workers: chunks + graph paths
  Workers-->>Orch: domain artifacts
  Orch->>Orch: aggregate + draft answer
  Orch->>Val: validate + compliance
  Val-->>Orch: ok + proposed_actions
  opt mutating_action
    Orch->>HITL: interrupt pending approval
    HITL-->>API: pending card
    User->>API: approve action
    API->>HITL: resume
    HITL-->>Orch: approved
    Orch->>MCP: create ServiceNow INC
    MCP-->>Orch: ticket_id
  end
  Orch-->>API: answer + citations + actions
  API-->>User: SSE stream
```
