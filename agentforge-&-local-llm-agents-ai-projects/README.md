# AgentForge & Local LLM Agents

Local-first AI agents portfolio: learn the building blocks in Jupyter, then run the same ideas as a deployable platform on **Ollama**.

| Project | Folder | Role | Status |
|---------|--------|------|--------|
| **Local LLM Agents** | [`local-llm-agents/`](local-llm-agents/) | Notebooks: RAG → one agent → multi-agent | Implemented |
| **AgentForge** | [`agentforge/`](agentforge/) | LangGraph + FastAPI + Streamlit product surface | Implemented (v0.1.0) |

As-built record: [`AS_BUILT.md`](AS_BUILT.md)

## Architecture

Learn→ship overview: [`docs/architecture.md`](docs/architecture.md) · [agentforge](agentforge/docs/architecture.md) · [local-llm-agents](local-llm-agents/docs/architecture.md)

---

## What this portfolio demonstrates

1. **PDF RAG** with a local LLM (TF-IDF in notebooks → Chroma + Ollama embeddings in AgentForge)
2. **Tool calling** — PDF search, weather, markdown study notes
3. **Multi-agent collaboration** — Research → Writer (notebooks) / LangGraph supervisor + workers (AgentForge)
4. **Local-first runtime** — no cloud LLM required for the happy path

```text
local-llm-agents (learn)          agentforge (ship)
────────────────────────          ─────────────────
TF-IDF + Jupyter                  Chroma + embeddings
Ad-hoc agent cells                LangGraph supervisor
Print / study_note.md             FastAPI SSE + Streamlit
No persistence / guardrails       SQLite + Chroma memory, guardrails, eval, Docker/k8s
```

---

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) running locally

```bash
ollama pull qwen3
ollama pull nomic-embed-text   # AgentForge only
```

---

## Suggested path

### 1. Learning track — `local-llm-agents`

```bash
cd local-llm-agents
pip install -r requirements.txt
jupyter lab
```

Run notebooks in order: `1_rag.ipynb` → `2_one_agent.ipynb` → `3_multi_agent.ipynb`.  
Details: [`local-llm-agents/README.md`](local-llm-agents/README.md) · [`local-llm-agents/reproduce.md`](local-llm-agents/reproduce.md)

### 2. Production track — `agentforge`

```bash
cd agentforge
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # or: cp .env.example .env
```

Place a PDF in `agentforge/assets/`, then:

```bash
uvicorn app.main:app --reload --port 8000
# separate terminal
streamlit run ui/streamlit_app.py
```

- API docs: http://localhost:8000/docs  
- UI: http://localhost:8501  
- Docker: `docker compose up --build` from `agentforge/`

Details: [`agentforge/README.md`](agentforge/README.md)

---

## Documentation map

| Doc | Purpose |
|-----|---------|
| [`docs/architecture.md`](docs/architecture.md) | Portfolio HLA (learn→ship) |
| [`AS_BUILT.md`](AS_BUILT.md) | Portfolio-level locked decisions |
| [`local-llm-agents/AS_BUILT.md`](local-llm-agents/AS_BUILT.md) | Notebook series as delivered |
| [`agentforge/AS_BUILT.md`](agentforge/AS_BUILT.md) | Platform architecture, API, deploy |

Canonical notebook series lives under `local-llm-agents/` (`1_rag.ipynb` → `2_one_agent.ipynb` → `3_multi_agent.ipynb`).
