# Architecture

Canonical HLA/LLA for RoboForge AI. Narrative design: [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md). Locked decisions: [`../AS_BUILT.md`](../AS_BUILT.md).

## High-Level Architecture (HLA)

Adapted from [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) §3.

```mermaid
flowchart LR
  subgraph input [Intake]
    Docs[Docs_RFP_SOW]
    CloudMock[Cloud_Inventory_Mocks]
    CodeMock[Legacy_Repo_Mocks]
  end
  subgraph runtime [Forge_Runtime]
    API[FastAPI_8003]
    LG[LangGraph_Supervisor]
  end
  subgraph knowledge [Knowledge_Plane]
    Vec[Hybrid_Index]
    Neo[Neo4j_GraphRAG]
    Mem[Three_Memory_Layers]
  end
  subgraph models [Model_Plane]
    Bedrock[AWS_Bedrock]
    Vertex[GCP_Vertex]
  end
  subgraph quality [Quality_Plane]
    Judges[Judge_Gate]
    LS[LangSmith]
    RedTeam[Injection_Suite]
  end

  Docs --> API
  CloudMock --> API
  CodeMock --> API
  API --> LG
  LG --> Vec
  LG --> Neo
  LG --> Mem
  LG --> Bedrock
  LG --> Vertex
  Judges --> LS
  RedTeam --> LS
```

Workers: `intake_analyzer` → `estate_assessor` → `knowledge_builder` → `security_compliance` → `solution_architect` → `roi_optimizer` → `judge_gate` → `hitl` → `delivery_publish`.

## Low-Level Architecture (LLA)

Engagement forge happy path with executive HITL before delivery-pack publish.

```mermaid
sequenceDiagram
  participant User
  participant API as FastAPI_8003
  participant Sup as Supervisor
  participant Intake as IntakeAnalyzer
  participant Estate as EstateAssessor
  participant Know as KnowledgeBuilder
  participant Sec as SecurityCompliance
  participant Arch as SolutionArchitect
  participant ROI as ROIOptimizer
  participant Judge as JudgeGate
  participant HITL as HITL
  participant Pub as DeliveryPublish

  User->>API: POST /forge or /forge/demo
  API->>Sup: start engagement thread
  Sup->>Intake: analyze intake pack
  Intake-->>Sup: intake
  Sup->>Estate: score cloud + legacy mocks
  Estate-->>Sup: estate
  Sup->>Know: hybrid RAG + GraphRAG evidence
  Know-->>Sup: evidence
  Sup->>Sec: control mapping + gaps
  Sec-->>Sup: security_findings
  Sup->>Arch: Bedrock-first blueprint
  Arch-->>Sup: blueprint
  Sup->>ROI: cost + payback model
  ROI-->>Sup: roi
  Sup->>Judge: architecture / groundedness / security / cost
  Judge-->>Sup: judge_scores pass
  Sup->>HITL: interrupt for executive approval
  HITL-->>API: pending card
  User->>API: POST /approve/{thread_id}
  API->>HITL: resume approved
  HITL-->>Sup: approval
  Sup->>Pub: publish delivery pack + episodic lesson
  Pub-->>Sup: published
  Sup-->>API: delivery_pack_id
  API-->>User: roadmap + risk matrix
```
