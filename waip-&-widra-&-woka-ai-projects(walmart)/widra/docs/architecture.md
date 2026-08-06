# Architecture

Canonical HLA/LLA for WIDRA (Walmart Intelligent Document Retrieval Assistant).

**Relation to prior docs:** An earlier uppercase `ARCHITECTURE.md` in this folder held the same Mermaid HLA plus storage/auth deep-dives. This Wave-1 `architecture.md` is the canonical entry point (HLA + LLA sequence). Extended ingestion/storage tables remain useful context in [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) and [`../AS_BUILT.md`](../AS_BUILT.md).

**Port:** FastAPI console **8005**.

## High-Level Architecture (HLA)

```mermaid
flowchart TB
  subgraph channels [Channels]
    UI[Web_Console]
    API[REST_SSE_API]
  end
  subgraph gateway [Edge]
    WAF[WAF_RateLimit]
    OIDC[OAuth2_OIDC_v2]
  end
  subgraph query [Query_Service]
    BFF[FastAPI_BFF]
    SUP[LangGraph_Supervisor]
    RET[Retrieval_Agent]
    ANS[Answer_Agent]
    AUTH[Auth_Agent]
    OBS[Observability_Agent]
  end
  subgraph ingest [Ingestion_Pipeline]
    UP[Upload_S3_Trigger]
    PARSE[PDF_Parser]
    CHUNK[Chunker]
    EMB[Embedder]
    IDX[Index_Writer]
  end
  subgraph storage [Storage_Tier]
    S3[(S3_MinIO)]
    PG[(PostgreSQL)]
    VDB[(Pinecone_Weaviate)]
  end
  subgraph models [Model_Gateway]
    LLM[Chat_Bedrock_Vertex_fake]
    EMBM[Embeddings]
  end

  UI --> API --> WAF --> BFF
  BFF --> SUP
  SUP --> AUTH --> RET --> ANS --> OBS
  RET --> VDB
  RET --> PG
  ANS --> LLM
  RET --> EMBM
  UP --> S3 --> PARSE --> CHUNK --> EMB --> IDX
  IDX --> VDB
  IDX --> PG
  EMB --> EMBM
```

## Low-Level Architecture (LLA)

Happy path: authorized conversational query with citations (hot path).

```mermaid
sequenceDiagram
  participant User
  participant API as FastAPI_8005
  participant Sup as Supervisor
  participant Auth as AuthAgent
  participant Ret as RetrievalAgent
  participant VDB as VectorDB
  participant PG as PostgreSQL
  participant Ans as AnswerAgent
  participant LLM as ModelGateway
  participant Obs as ObservabilityAgent

  User->>API: POST /query
  API->>Sup: start query thread
  Sup->>Auth: resolve roles → ACL scope
  Auth-->>Sup: allowed policy_ids, regions, depts
  Sup->>Ret: rewrite + hybrid search
  Ret->>VDB: dense+BM25 with ACL prefilter
  VDB-->>Ret: candidate chunks
  Ret->>PG: metadata join
  PG-->>Ret: chunk rows
  Ret-->>Sup: top5 reranked
  Sup->>Ans: grounded generate
  Ans->>LLM: context + citations
  LLM-->>Ans: answer + table facts
  Ans-->>Sup: cited answer
  Sup->>Obs: emit metrics + audit
  Obs-->>Sup: traced
  Sup-->>API: response
  API-->>User: answer + [doc_id, page, snippet]
```
