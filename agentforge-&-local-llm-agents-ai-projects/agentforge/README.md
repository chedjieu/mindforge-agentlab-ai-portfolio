# AgentForge

Local-first **production-oriented** agentic AI platform built on Ollama.

AgentForge evolves the educational notebooks in `../local-llm-agents` into a deployable system with:

- **LangGraph** stateful multi-agent orchestration
- **ChromaDB** semantic vector search
- **Ollama embeddings** (`nomic-embed-text`) instead of TF-IDF
- **Pydantic** structured outputs and settings
- **FastAPI** + SSE streaming
- **Streamlit** chat UI
- Short-term memory (SQLite checkpointer) + long-term memory (Chroma)
- Guardrails for prompt injection and ungrounded answers
- DeepEval-backed evaluation endpoint (with lexical fallback)
- OpenTelemetry tracing (+ optional Langfuse via env)
- Docker Compose and starter Kubernetes manifests

## Architecture

HLA + `/chat` sequence: [`docs/architecture.md`](docs/architecture.md) · as-built: [`AS_BUILT.md`](AS_BUILT.md)

```
User → Streamlit / FastAPI (SSE)
         → Guardrails
         → LangGraph Supervisor
              ├─ Research (Chroma RAG)
              ├─ Tools (PDF / Weather / Notes / Memory)
              └─ Writer (Markdown study notes)
         → Sqlite checkpointer + Chroma long-term memory
```

## Quickstart

### 1. Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) running locally

```bash
ollama pull qwen3
ollama pull nomic-embed-text
```

### 2. Install

```bash
cd agentforge
# Preferred (LangGraph 1.x locked via uv.lock):
uv sync
copy .env.example .env   # or cp on macOS/Linux

# Or with pip:
python -m venv .venv
# Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add a PDF

Place a PDF in `assets/` (for example the certification PDF used by the notebooks).

### 4. Run API

```bash
uvicorn app.main:app --reload --port 8000
```

### 5. Ingest + chat

```bash
curl -X POST http://localhost:8000/ingest -H "Content-Type: application/json" -d "{}"
curl -X POST http://localhost:8000/chat -H "Content-Type: application/json" -d "{\"message\":\"What topics are covered?\",\"stream\":false}"
```

### 6. Streamlit UI

```bash
streamlit run ui/streamlit_app.py
```

## Docker

```bash
docker compose up --build
```

- API: http://localhost:8000/docs
- UI: http://localhost:8501

Ensure Ollama is reachable from containers (`OLLAMA_HOST=http://host.docker.internal:11434` by default).

## Kubernetes

Starter manifests live in `k8s/deployment.yaml`. Build/load the image as `agentforge:latest`, then:

```bash
kubectl apply -f k8s/deployment.yaml
```

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness + index count |
| `POST /ingest` | PDF → embeddings → Chroma |
| `POST /chat` | Agent turn (SSE when `stream=true`) |
| `POST /eval` | Sample DeepEval / fallback metrics |

## How this differs from `local-llm-agents`

| Notebook demo | AgentForge |
|---|---|
| TF-IDF cosine search | Ollama embeddings + Chroma |
| Linear notebook cells | LangGraph supervisor graph |
| Ad-hoc prints | FastAPI + Streamlit product surface |
| No persistence | SQLite threads + long-term memory |
| No safety layer | Injection + groundedness guardrails |
| Manual checks | `/eval` pipeline + OpenTelemetry |

## Tests

```bash
uv sync --extra dev
uv run pytest -q
```

## CI gates

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to `main`/`master`:

| Gate | Command |
|---|---|
| Lint | `uv run ruff check` on `app`, `tests`, `ui`, `security`, `evals` (paths that exist) |
| Unit tests | `uv run pytest -q` |
| Smoke evals | `uv run python evals/run_all.py` (graph compile + guardrail happy path) |
| Injection suite | `uv run python security/injection_eval.py` (>=95% block/escalate on 50 attacks) |

Local equivalent:

```bash
uv sync --frozen --extra dev
uv run ruff check app tests ui security evals
uv run pytest -q
uv run python evals/run_all.py
uv run python security/injection_eval.py
```

## Configuration

See [`.env.example`](.env.example) for Ollama hosts, model names, Chroma/SQLite paths, retrieval thresholds, and optional Langfuse / OTLP settings.
