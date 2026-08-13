# High-level architecture (HLA)

C4 context and container view of RAIP. Implementation detail lives in [LOW_LEVEL.md](LOW_LEVEL.md). Locked as-built: [`../../AS_BUILT.md`](../../AS_BUILT.md).

**Port:** FastAPI review console **8011**. Env prefix: `RAIP_*`.

## Intent

RAIP drafts clinical/regulatory **document sections** from approved, versioned sources. Generation is subordinate to evidence. An unsupported material claim cannot publish, even if the aggregate quality score is high.

This is **not** a chatbot, not CarePath CDS, and not a HIPAA certification.

## System context (C4 L1)

Authors and reviewers use one console. Approved PDFs enter through ingest. The API owns orchestration, evidence, and audit. Humans remain on the publication path.

```mermaid
flowchart LR
  Author[Author]
  Reviewer[Reviewer]
  Auditor[Auditor]
  Src[Approved_PDFs]
  RAIP[RAIP_console_API_8011]
  Cloud[Bedrock_or_Vertex_optional]
  Author --> RAIP
  Reviewer --> RAIP
  Auditor --> RAIP
  Src --> RAIP
  RAIP --> Cloud
```

| Actor | Intent |
|-------|--------|
| Author | Upload sources, request a section draft, inspect claims |
| Reviewer | Approve, edit, or reject; HITL is required in demo mode |
| Auditor | Reconstruct `request_id` → sources, claims, scores, decision |
| Source PDFs | Untrusted **data**, never instructions |

## Container view (C4 L2)

```mermaid
flowchart TB
  subgraph clients [Clients]
    UI[HTML_review_console]
  end
  subgraph runtime [Runtime]
    API[FastAPI]
    LG[LangGraph_supervisor]
    W[Ingest_worker]
  end
  subgraph data [Data_plane]
    DB[SQLite_or_Postgres]
    Vec[Vector_adapter]
    G[Graph_store]
    Obj[Object_store]
  end
  subgraph models [Model_plane]
    Fake[Fake_CI]
    Bedrock[AWS_Bedrock]
    Vertex[GCP_Vertex]
  end
  UI --> API
  API --> LG
  API --> W
  W --> DB
  W --> Vec
  W --> G
  W --> Obj
  LG --> DB
  LG --> Vec
  LG --> G
  LG --> Fake
  LG --> Bedrock
  LG --> Vertex
```

| Container | Responsibility |
|-----------|----------------|
| Review console | 3-pane UI: query/sources, draft, claims/evidence/scores |
| FastAPI | Auth headers, upload, draft invoke, HITL resume, audit |
| LangGraph | Supervisor loop; workers never peer-route |
| Ingest worker | Parse → chunk → embed → register evidence + graph edges |
| Metadata DB | Tenants, versions, chunks, drafts, jobs, audit (source of truth) |
| Vector adapter | Dense embeddings; cosine locally, pgvector/Pinecone as path |
| Graph store | Supersession + claim–evidence edges; Neo4j optional |
| Object store | Raw PDF bytes; local disk or S3/GCS adapter |
| Model gateway | `RAIP_MODEL=fake` in CI; Bedrock/Vertex in production |

## Authoring workflow

Happy path. Failure states are first-class (`INSUFFICIENT_EVIDENCE`, `GROUNDING_FAILED`, `PUBLICATION_BLOCKED`, …). Critical evidence failure emits an **EVIDENCE GAP** rather than filling from model knowledge.

```mermaid
sequenceDiagram
  participant Author
  participant API
  participant FW as Firewall
  participant Ret as Retrieval
  participant Syn as Synthesis
  participant Draft as Drafting
  participant CV as ClaimVerify
  participant QG as QualityGates
  participant Pub as PubGate
  participant HITL
  Author->>API: POST /authoring/draft
  API->>FW: scan user request
  FW->>Ret: hybrid plus GraphRAG
  Ret->>Syn: evidence bundle
  Syn->>Draft: evidence_map only
  Draft->>CV: extract and match claims
  CV->>QG: support status plus scores
  QG->>Pub: critical failure overrides score
  Pub->>HITL: interrupt if RAIP_HITL=required
  HITL-->>Author: approve edit reject
```

## Trust boundaries

1. **User request** — may be blocked on jailbreak (`firewall`).
2. **Source documents** — always untrusted data; delimited in prompts.
3. **Retrieval index** — tenant-filtered; superseded versions dropped by default.
4. **Draft output** — claim-verified before HITL.
5. **Publication** — boolean AND of gates **and** human approval.

## Quality and publication policy

Configurable weights produce an aggregate score. **Any critical gate failure sets `PUBLICATION_BLOCKED`**, regardless of that score.

```
APPROVED iff
  grounding PASS
  AND citation PASS
  AND safety PASS
  AND regulatory PASS
  AND template PASS
  AND security PASS
  AND human approval
```

## Deployment shapes

| Shape | What runs |
|-------|-----------|
| Local (default) | One FastAPI process; SQLite; in-memory graph; fake model |
| Docker Compose | API + worker + Postgres+pgvector + Neo4j |
| Production path | Same containers behind HTTPS; RDS; Neo4j Aura; S3/GCS; Bedrock or Vertex; OIDC. **Not applied in this repo.** |

See [LOCAL_VS_PRODUCTION.md](LOCAL_VS_PRODUCTION.md) and [PILOT_TO_SCALE.md](PILOT_TO_SCALE.md).

## What this HLA deliberately omits

Kubernetes, Kafka, live EHR/FHIR, production OCR, ClamAV, and a React SPA. Those are documented as non-goals or later phases, not implied by the container diagram.
