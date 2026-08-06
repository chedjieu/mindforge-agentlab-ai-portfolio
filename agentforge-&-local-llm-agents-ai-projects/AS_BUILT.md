# As-Built — AgentForge & Local LLM Agents Portfolio

**Document type:** Portfolio planning documentation — *as built*  
**Folder:** `8.agentforge-&-local-llm-agents-ai-projects/`  
**Theme:** Local-first AI agents — from educational notebooks to a production-oriented platform

---

## Purpose

This portfolio pairs a **learning track** with a **productized evolution** of the same ideas (PDF RAG, tools, multi-agent study notes), all running on **Ollama** locally.

| Project | Role | As-built doc |
|---------|------|--------------|
| [`local-llm-agents/`](local-llm-agents/) | Hands-on notebooks: RAG → one agent → multi-agent | [local-llm-agents/AS_BUILT.md](local-llm-agents/AS_BUILT.md) |
| [`agentforge/`](agentforge/) | Deployable LangGraph + FastAPI + Streamlit platform | [agentforge/AS_BUILT.md](agentforge/AS_BUILT.md) |

Canonical notebook series lives under `local-llm-agents/` (`1_rag.ipynb` → `2_one_agent.ipynb` → `3_multi_agent.ipynb`).

---

## Locked portfolio decisions

| Area | Decision |
|------|----------|
| Naming | Parent folder named after child projects (`agentforge` + `local-llm-agents`) |
| LLM stack | Local Ollama (`qwen3`); AgentForge also uses `nomic-embed-text` |
| Learning → production | Notebooks stay TF-IDF/Jupyter; AgentForge replaces retrieval/orchestration/surface |
| Cloud | Not required for the happy path |
| Sibling boundary | Does not replace enterprise HITL / GraphRAG portfolios (CarePath, RoboForge, etc.) |

---

## Suggested path

1. Run `local-llm-agents` notebooks in order (`reproduce.md`).  
2. Stand up AgentForge (`README.md`: ingest → `/chat` → Streamlit).  
3. Compare behaviors using the differentiation tables in each project’s `AS_BUILT.md`.

---

## Verification

- [x] Both subprojects present with README + AS_BUILT  
- [x] AgentForge API/UI/Docker/k8s stubs delivered  
- [x] Notebook progression and reproduce runbook delivered  
