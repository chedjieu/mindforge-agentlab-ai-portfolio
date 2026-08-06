# Architecture

Local-first agents portfolio: learn building blocks in Jupyter, then ship the same ideas as a deployable platform on Ollama.

| Track | Folder | Docs |
|-------|--------|------|
| Learn | [`local-llm-agents/`](../local-llm-agents/) | [architecture](../local-llm-agents/docs/architecture.md) |
| Ship | [`agentforge/`](../agentforge/) | [architecture](../agentforge/docs/architecture.md) |

## High-Level Architecture (HLA)

```mermaid
flowchart LR
  Learn[local_llm_agents]
  Ship[agentforge]

  Learn -->|evolve_ideas| Ship

  subgraph LearnTrack["learn_notebooks"]
    N1[1_rag_TFIDF]
    N2[2_one_agent]
    N3[3_multi_agent]
    N1 --> N2 --> N3
  end

  subgraph ShipTrack["ship_platform"]
    UI[Streamlit_8501]
    API[FastAPI_8000]
    GF[Input_Guardrails]
    SUP[LangGraph_Supervisor]
    RAG[Chroma_plus_Ollama_embed]
    MEM[Sqlite_plus_Chroma_memory]
    UI --> API --> GF --> SUP
    SUP --> RAG
    SUP --> MEM
  end

  Learn --> LearnTrack
  Ship --> ShipTrack
```

**Runtime (AgentForge):** Ollama `qwen3` + `nomic-embed-text` · API `http://localhost:8000/docs` · UI `http://localhost:8501`.

## Low-Level Architecture (LLA)

### LLA omitted (portfolio root)

Portfolio-level flow is learn → ship. Detailed `/chat` sequence lives in [`agentforge/docs/architecture.md`](../agentforge/docs/architecture.md). Notebook path LLA is omitted in [`local-llm-agents/docs/architecture.md`](../local-llm-agents/docs/architecture.md).
