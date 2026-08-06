# Architecture

AgentForge — local-first LangGraph + FastAPI + Streamlit platform on Ollama (v0.1.0).

## High-Level Architecture (HLA)

Adapted from [`AS_BUILT.md`](../AS_BUILT.md).

```mermaid
flowchart TD
  User[User]
  UI[Streamlit_UI]
  API[FastAPI_SSE]
  GF[Input_Guardrails]
  HTTP400[HTTP_400]
  SUP[LangGraph_Supervisor]
  RES[research]
  TOOLS[tools]
  WR[writer]
  ANS[answer]
  RAG[Chroma_agentforge_docs]
  LTM[Chroma_agentforge_memory]
  REG[TOOL_REGISTRY]
  GND[Groundedness]
  CP[(Sqlite_checkpointer)]

  User --> UI
  User --> API
  UI --> API
  API --> GF
  GF -->|allow| SUP
  GF -->|deny| HTTP400
  SUP --> RES
  SUP --> TOOLS
  SUP --> WR
  SUP --> ANS
  RES --> RAG
  RES --> LTM
  TOOLS --> REG
  ANS --> GND
  SUP -.-> CP
```

**Workers:** `research` · `tools` · `writer` · `answer` (supervisor routes; workers never call each other).  
**Ports:** API `8000` · Streamlit `8501` · Ollama `11434`.

## Low-Level Architecture (LLA)

`POST /chat` turn (SSE when `stream=true`).

```mermaid
sequenceDiagram
  participant Client as Streamlit_or_curl
  participant API as FastAPI_chat
  participant GF as validate_user_message
  participant SUP as supervisor
  participant RES as research
  participant TOOLS as tools_node
  participant WR as writer
  participant ANS as answer
  participant RAG as Chroma_docs_memory
  participant CP as Sqlite_checkpointer

  Client->>API: POST_/chat_message_thread_id
  API->>GF: non_empty_max_len_injection
  alt injection_or_invalid
    GF-->>Client: HTTP_400
  else allowed
    GF->>SUP: AgentState
    SUP->>CP: load_thread
    alt route_research
      SUP->>RES: route_research
      RES->>RAG: retrieve_top4_plus_memory
      RES-->>SUP: context_citations
      SUP->>ANS: or_writer_if_study_note
    else route_tools
      SUP->>TOOLS: TOOL_REGISTRY
      TOOLS-->>SUP: tool_result
      SUP->>ANS: route_answer
    else route_writer
      SUP->>WR: write_study_note
      WR-->>Client: draft_END
    else route_answer
      SUP->>ANS: grounded_answer
    end
    ANS->>RAG: groundedness_check
    ANS-->>API: answer_route_citations_events
    API->>CP: persist_thread
    API-->>Client: JSON_or_SSE_final
  end
```
