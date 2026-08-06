# Architecture

Canonical HLA/LLA for WOKA (Walmart OmniKnowledge AI). Extended layer notes historically lived in uppercase `ARCHITECTURE.md`; this file is the Wave-1 canonical view. See also [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) and [`../AS_BUILT.md`](../AS_BUILT.md).

**Port:** FastAPI BFF **8006**.

## High-Level Architecture (HLA)

ASCII layers converted to Mermaid:

```mermaid
flowchart TB
  subgraph channels [Channels]
    UI[Web_Console]
  end
  subgraph edge [Edge]
    GW[API_Gateway_WAF]
  end
  subgraph runtime [Runtime]
    BFF[FastAPI_BFF_8006]
    Sec[Security_Agent]
    Orch[LangGraph_Orchestrator]
    Ret[Retrieval_Agent]
    Doc[Document_Agent]
    SQL[SQL_Agent]
    Net[Internet_Agent]
    Comp[Compliance_Agent]
    Cite[Citation_Agent]
    An[Analytics_Agent]
    Obs[Observability_Agent]
  end
  subgraph models [Model_Gateway]
    Bedrock[Bedrock]
    Vertex[Vertex]
    Fake[fake]
  end
  subgraph storage [Storage]
    MinIO[(MinIO)]
    PG[(Postgres)]
    WV[(Weaviate)]
    Neo[(Neo4j_or_JSONL)]
  end
  Audit[Audit_LangSmith]

  UI --> GW --> BFF --> Sec --> Orch
  Orch --> Ret
  Orch --> Doc
  Orch --> SQL
  Orch --> Net
  Orch --> Comp
  Orch --> Cite
  Orch --> An
  Orch --> Obs
  Orch --> Bedrock
  Orch --> Vertex
  Orch --> Fake
  Ret --> WV
  Ret --> Neo
  Doc --> MinIO
  SQL --> PG
  Obs --> Audit
```

## Low-Level Architecture (LLA)

Happy path: supply-chain disruption query (UC-1) with parallel agents → compliance → citations.

```mermaid
sequenceDiagram
  participant User
  participant API as FastAPI_8006
  participant Sec as SecurityAgent
  participant Orch as Orchestrator
  participant Ret as RetrievalAgent
  participant Doc as DocumentAgent
  participant SQL as SQLAgent
  participant Net as InternetAgent
  participant Comp as ComplianceAgent
  participant Cite as CitationAgent
  participant LLM as ModelGateway

  User->>API: POST query SSE
  API->>Sec: RBAC_ABAC scope
  Sec-->>API: allowed policies regions clearance
  API->>Orch: plan agent set
  par parallel_agents
    Orch->>Ret: hybrid + GraphRAG
    Ret-->>Orch: evidence
    Orch->>Doc: parse table facts
    Doc-->>Orch: doc_artifacts
    Orch->>SQL: mock inventory SQL
    SQL-->>Orch: sql_rows
    Orch->>Net: FDA_OSHA_weather mocks
    Net-->>Orch: external_facts
  end
  Orch->>Orch: merge artifacts
  Orch->>Comp: compliance check
  Comp-->>Orch: ok
  Orch->>Cite: attach citations
  Cite->>LLM: finalize answer
  LLM-->>Cite: response
  Cite-->>Orch: answer + confidence + step_log
  Orch-->>API: final_response
  API-->>User: SSE stream
```
