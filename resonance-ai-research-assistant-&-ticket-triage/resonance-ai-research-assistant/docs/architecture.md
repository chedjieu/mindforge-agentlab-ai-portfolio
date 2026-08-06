# Architecture

Canonical HLA/LLA for the Resonance AI Research Assistant. There is no standalone `SYSTEM_DESIGN.md` in this package; HLA is extracted from the README Mermaid / ASCII flow. Locked decisions: [`../AS_BUILT.md`](../AS_BUILT.md).

## High-Level Architecture (HLA)

```mermaid
flowchart LR
  User --> UI[FastAPI_UI_8000]
  UI -->|POST_research| LG[LangGraph]
  LG --> Recall[recall]
  Recall --> Planner[planner]
  Planner --> Researcher[researcher]
  Researcher --> Writer[writer]
  Writer --> Guard[guard]
  Guard --> Extract[extract]
  Extract --> END[END]
  Researcher --> Web[Tavily_Web]
  Researcher --> Local[pgvector_Corpus]
  LG --> LLM[Bedrock_or_Vertex]
```

| Node | Role |
|------|------|
| `recall` | Semantic memory facts for the session |
| `planner` | 3–7 sub-questions (`web` \| `local` \| `both`) |
| `researcher` | Tools ≤ 4 calls / sub-question |
| `writer` | Cited Markdown report |
| `guard` | Citation / URL validator |
| `extract` | Optional durable `remember()` |

## Low-Level Architecture (LLA)

Happy path: research question → cited report via SSE.

```mermaid
sequenceDiagram
  participant User
  participant API as FastAPI_8000
  participant Recall as recall
  participant Planner as planner
  participant Res as researcher
  participant Local as pgvector
  participant Web as Tavily
  participant Writer as writer
  participant Guard as guard
  participant Extract as extract

  User->>API: POST /research
  API->>Recall: load semantic memory
  Recall-->>API: memory facts
  API->>Planner: plan sub-questions
  Planner-->>API: sub_questions
  loop each_sub_question
    API->>Res: research step
    opt local_or_both
      Res->>Local: search_local_docs
      Local-->>Res: chunks
    end
    opt web_or_both
      Res->>Web: web_search / fetch_url
      Web-->>Res: snippets
    end
    Res-->>API: findings
  end
  API->>Writer: draft Markdown + citations
  Writer-->>API: report
  API->>Guard: validate citations vs tool findings
  Guard-->>API: validated report
  opt remember_fact
    API->>Extract: extract durable fact
  end
  API-->>User: SSE /stream/{thread_id}
```
