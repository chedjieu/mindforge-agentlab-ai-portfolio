# Architecture

Canonical high-level and low-level views for the Agentic RAG Chatbot. Detailed design: [system_design.md](system_design.md).

## High-Level Architecture (HLA)

```mermaid
flowchart LR
  User -->|chat| n8nChat[n8n_Chat_UI]
  n8nChat --> n8nWF[n8n_Workflow]
  n8nWF -->|POST_chat| API[FastAPI]
  API --> Agent[LangChain_Agent]
  Agent --> Retriever[Chroma_Retriever]
  Agent --> Tools[Agent_Tools]
  Retriever --> Chroma[(ChromaDB)]
  Agent --> LLM[OpenAI_GPT4o]
  n8nWF --> Log[Query_Logs]
  n8nWF --> Ext[Slack_or_Webhook]
```

| Component | Role |
|-----------|------|
| n8n Chat UI / Workflow | Chat surface, HTTP orchestration, session logs, optional escalation |
| FastAPI (`/chat`, `/ingest`, `/health`) | API contract for n8n |
| LangChain agent | Tool-calling loop; prefers KB search first |
| ChromaDB | Local persistent vector index (`lilian_weng_kb`) |
| Tools | `search_knowledge_base_tool`, `get_source_summary`, `web_search` |
| OpenAI | Embeddings + GPT-4o generation |

## Low-Level Architecture (LLA)

Happy path: user question grounded in the Lilian Weng KB.

```mermaid
sequenceDiagram
  participant User
  participant n8n as n8n_Workflow
  participant API as FastAPI
  participant Agent as LangChain_Agent
  participant Chroma as ChromaDB
  participant Tools as Agent_Tools
  participant LLM as OpenAI

  User->>n8n: chat message
  n8n->>API: POST /chat {message, session_id}
  API->>Agent: invoke agent loop
  Agent->>LLM: plan next tool / answer
  Agent->>Chroma: search_knowledge_base_tool
  Chroma-->>Agent: top-k chunks + metadata
  opt weak_or_out_of_kb
    Agent->>Tools: get_source_summary / web_search
    Tools-->>Agent: summaries or web snippets
  end
  Agent->>LLM: synthesize cited answer
  LLM-->>Agent: final answer + sources
  Agent-->>API: answer, sources, tool_steps
  API-->>n8n: JSON response
  n8n->>n8n: write session log
  opt escalate_or_error
    n8n->>n8n: Slack / webhook alert
  end
  n8n-->>User: formatted reply
```
