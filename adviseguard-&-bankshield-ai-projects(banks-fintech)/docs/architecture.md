# Architecture

Portfolio overview for two sibling LangGraph fintech platforms. Neither package imports or calls the other at runtime.

| Project | Port | Architecture |
|---------|-----:|--------------|
| [`bankshield-ai/`](../bankshield-ai/) | 8003 | [docs/architecture.md](../bankshield-ai/docs/architecture.md) |
| [`adviseguard-ai/`](../adviseguard-ai/) | 8004 | [docs/architecture.md](../adviseguard-ai/docs/architecture.md) |

## High-Level Architecture (HLA)

```mermaid
flowchart TB
  subgraph Shared["shared_platform_pattern"]
    UI[FastAPI_console]
    SUP[LangGraph_supervisor]
    RAG[Hybrid_RAG_Chroma_BM25]
    KG[Neo4j_or_JSON_KG]
    JUDGE[LLM_judges]
    HITL[HITL_interrupt]
    PUB[publish_audit_log]
    UI --> SUP --> RAG
    SUP --> KG
    SUP --> JUDGE --> HITL --> PUB
  end

  BS[bankshield_ai_8003]
  AG[adviseguard_ai_8004]
  BS -.-> Shared
  AG -.-> Shared
```

**Ports:** BankShield UI `8003` · AdviseGuard UI `8004` · Neo4j `7687` / `7688` · Postgres `5434` / `5435`.

## Low-Level Architecture (LLA)

### LLA omitted (portfolio root)

Per-product HITL sequences are documented in each package’s `docs/architecture.md`. This file only orients the sibling relationship and shared stack.
