# Architecture

BankShield AI — multi-agent financial-crime investigation (alert → evidence → HITL → SAR draft).

See also [`SYSTEM_DESIGN.md`](SYSTEM_DESIGN.md) · [`AS_BUILT.md`](../AS_BUILT.md).

## High-Level Architecture (HLA)

```mermaid
flowchart TD
  Alert[Alert_queue]
  API[FastAPI_8003]
  SUP[LangGraph_supervisor]
  TRI[triage_router]
  KYC[identity_kyc]
  TXN[transaction_intel]
  GW[graph_walker]
  REG[regulatory_rag]
  SIM[similar_case_retriever]
  RISK[risk_scorer]
  REC[recommender]
  GND[grounder_judge]
  HITL[hitl_interrupt]
  SAR[sar_publisher]
  LOG[(published_cases_log)]
  Neo[(Neo4j_or_JSON_KG)]
  Chroma[(Chroma_plus_BM25)]

  Alert --> API --> SUP
  SUP --> TRI
  SUP --> KYC
  SUP --> TXN
  SUP --> GW
  SUP --> REG
  SUP --> SIM
  SUP --> RISK
  SUP --> REC
  SUP --> GND
  SUP --> HITL
  SUP --> SAR
  GW --> Neo
  REG --> Chroma
  SIM --> Chroma
  SAR --> LOG
```

**HITL rule:** `risk_band in {high, critical}` or fraud types in `{wire, sanctions, aml, mule}` always interrupt before SAR publish. The system never auto-files a regulatory SAR without human approval on high-risk cases.

## Low-Level Architecture (LLA)

Investigation turn with human-in-the-loop.

```mermaid
sequenceDiagram
  participant Inv as Investigator_UI
  participant API as FastAPI
  participant SUP as supervisor
  participant W as evidence_workers
  participant RISK as risk_scorer
  participant REC as recommender
  participant GND as grounder_judge
  participant HITL as hitl_node
  participant SAR as sar_publisher
  participant LOG as published_cases_log

  Inv->>API: POST_/investigate_or_demo
  API->>SUP: InvestigationState_plus_Sqlite
  SUP->>W: triage_kyc_txn_graph_reg_similar
  W-->>SUP: evidence_graph_paths_citations
  SUP->>RISK: fuse_risk_band
  RISK-->>SUP: risk_score_band
  SUP->>REC: explainable_recommendation
  REC-->>SUP: evidence_ids_refs
  SUP->>GND: claim_evidence_check
  alt high_risk_or_sensitive
    GND->>HITL: interrupt_pending
    HITL-->>Inv: approval_payload
    Inv->>API: POST_/approve_edit_or_reject
    API->>HITL: resume_approval
  else auto_low_risk
    GND->>HITL: approval_auto
  end
  alt approved_or_edited
    HITL->>SAR: draft_SAR_package
    SAR->>LOG: append_publish
    SAR-->>Inv: case_closed_or_monitor
  else rejected
    HITL-->>Inv: END_no_publish
  end
```
