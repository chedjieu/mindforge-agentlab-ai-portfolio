# Architecture

Canonical HLA/LLA for the Panasonic Enterprise GenAI Knowledge Platform (`panasonic-egkp`). Full narrative design remains in [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md); as-built locks in [`../AS_BUILT.md`](../AS_BUILT.md). Prefer this file over duplicating divergent architecture diagrams in the README.

## High-Level Architecture (HLA)

Adapted from [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) §3.

```mermaid
flowchart LR
  subgraph clients [Clients]
    WebUI[Web_UI]
    APIClients[API_Clients]
  end
  subgraph edge [Edge]
    APIGW[API_Gateway]
    Auth[Auth_RBAC]
  end
  subgraph runtime [Agent_Runtime]
    FastAPI[FastAPI_8002]
    LG[LangGraph_Supervisor]
  end
  subgraph knowledge [Knowledge_Plane]
    Vec[Vector_Index]
    Neo[Neo4j_KG]
    Store[LangGraph_Store]
  end
  subgraph models [Model_Plane]
    Bedrock[AWS_Bedrock]
    Vertex[GCP_Vertex]
  end
  subgraph ingest [Ingest_Plane]
    SF[StepFunctions_or_CloudWorkflows]
    Bronze[Bronze_Raw]
    Silver[Silver_Parsed]
    Gold[Gold_Chunks_Entities]
  end
  subgraph quality [Quality_Plane]
    LS[LangSmith]
    Judges[LLM_as_Judge_Gates]
  end

  WebUI --> APIGW
  APIClients --> APIGW
  APIGW --> Auth --> FastAPI --> LG
  LG --> Vec
  LG --> Neo
  LG --> Store
  LG --> Bedrock
  LG --> Vertex
  SF --> Bronze --> Silver --> Gold
  Gold --> Vec
  Gold --> Neo
  Judges --> LS
  Judges -.-> LG
```

Workers (supervisor-owned; never peer-route): `intent_router` → `retriever` → `graph_walker` → `synthesizer` → `grounder` → `hitl` → `answer_publish`.

## Low-Level Architecture (LLA)

Supervisor + HITL happy path (sensitive / low-confidence answer approved and published).

```mermaid
sequenceDiagram
  participant User
  participant API as FastAPI_8002
  participant Sup as Supervisor
  participant IR as IntentRouter
  participant Ret as Retriever
  participant GW as GraphWalker
  participant Syn as Synthesizer
  participant Grd as Grounder
  participant HITL as HITL
  participant Pub as AnswerPublish

  User->>API: POST /ask
  API->>Sup: start thread
  Sup->>IR: classify query + role
  IR-->>Sup: domain, sensitivity, needs_graph
  Sup->>Ret: hybrid retrieve + ACL filter
  Ret-->>Sup: retrieved_chunks
  opt needs_graph
    Sup->>GW: entity hops less_eq_6
    GW-->>Sup: graph_paths
  end
  Sup->>Syn: draft with citations + memory
  Syn-->>Sup: draft_answer
  Sup->>Grd: claim-evidence check
  Grd-->>Sup: grounding_score ok
  Sup->>HITL: interrupt pending approval
  HITL-->>API: pending card
  User->>API: POST /approve/{thread_id}
  API->>HITL: resume approved
  HITL-->>Sup: approval
  Sup->>Pub: publish approved answer
  Pub-->>Sup: published
  Sup-->>API: final result
  API-->>User: cited answer
```
