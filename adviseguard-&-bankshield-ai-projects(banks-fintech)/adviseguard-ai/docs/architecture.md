# Architecture

AdviseGuard AI — personalized advice + fraud screening + customer support with HITL on high-stakes paths.

See also [`SYSTEM_DESIGN.md`](SYSTEM_DESIGN.md) · [`AS_BUILT.md`](../AS_BUILT.md).

## High-Level Architecture (HLA)

```mermaid
flowchart TD
  User[Customer_or_ops]
  API[FastAPI_8004]
  SUP[LangGraph_supervisor]
  INT[intent_router]
  RET[hybrid_retriever]
  GW[graph_walker]
  ADV[financial_advisor]
  FRD[fraud_detector]
  SUPP[customer_support]
  COMP[compliance_judge]
  RISK[risk_judge]
  SYN[synthesizer]
  HITL[hitl_node]
  PUB[response_publish]
  Neo[(Neo4j_or_JSON_KG)]
  Chroma[(Chroma_adviseguard_chunks)]

  User --> API --> SUP
  SUP --> INT
  SUP --> RET
  SUP --> GW
  SUP --> ADV
  SUP --> FRD
  SUP --> SUPP
  SUP --> COMP
  SUP --> RISK
  SUP --> SYN
  SUP --> HITL
  SUP --> PUB
  RET --> Chroma
  GW --> Neo
```

**UI:** `/` customer · `/ops` employee fraud dashboard · port `8004`.  
**HITL when:** fraud `risk_band` in `{high, critical}`, advice marked `high_stakes`, compliance &lt; 0.6, grounding &lt; 0.7, or soft-escalate injection patterns.

## Low-Level Architecture (LLA)

Ask / fraud demo turn with human-in-the-loop.

```mermaid
sequenceDiagram
  participant Client as Customer_or_Ops_UI
  participant API as FastAPI
  participant SUP as supervisor
  participant INT as intent_router
  participant RET as hybrid_retriever
  participant SPEC as advisor_fraud_or_support
  participant COMP as compliance_judge
  participant RISK as risk_judge
  participant SYN as synthesizer
  participant HITL as hitl_node
  participant PUB as response_publish

  Client->>API: POST_/ask_or_/fraud_demo
  API->>SUP: SessionState_plus_Sqlite
  SUP->>INT: classify_intent_flags
  INT-->>SUP: needs_rag_graph_specialists
  SUP->>RET: BM25_dense_RRF
  RET-->>SUP: retrieved_chunks
  SUP->>SPEC: domain_draft
  SPEC-->>SUP: advice_fraud_or_support
  SUP->>COMP: compliance_score
  SUP->>RISK: risk_score_band
  SUP->>SYN: final_response
  alt HITL_required
    SYN->>HITL: interrupt_pending
    HITL-->>Client: approval_payload
    Client->>API: POST_/approve_thread_id
    API->>HITL: resume_approval
  else auto_safe
    SYN->>HITL: approval_auto
  end
  alt approved_or_edited
    HITL->>PUB: publish_log
    PUB-->>Client: grounded_response
  else rejected
    HITL-->>Client: END_no_publish
  end
```
