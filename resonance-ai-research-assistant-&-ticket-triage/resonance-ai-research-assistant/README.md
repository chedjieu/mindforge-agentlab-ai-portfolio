# Resonance AI Research Assistant (LangGraph + LangChain + pgvector)

**Agentic research knowledge assistant** for the Resonance Technologies Agentic AI (Project 1).

Given a research question, the system plans sub-questions, retrieves from a local pgvector corpus and/or the live web (Tavily), writes a **cited Markdown report**, validates URLs against tool findings, and optionally stores a durable memory fact for the next session.

- **Orchestration:** LangGraph state machine (`recall → planner → researcher → writer → guard → extract`)
- **Models:** AWS Bedrock (`gpt-oss-120b`) or Google Vertex (`gemini-2.5-pro`) via a single `RAIRA_MODEL` switch; `fake` for offline demos
- **RAG:** pgvector (Docker) over sample corpora (AWS / Kubernetes / Anthropic policy)
- **UI:** FastAPI + HTMX + SSE streaming (no React/npm)
- **Deploy:** Google Cloud Run
- **Observability / evals:** LangSmith

Sibling Project 2 (ticket triage + HITL) lives in [`../resonance-ai-ticket-triage-agent/`](../resonance-ai-ticket-triage-agent/).  
Full as-built planning record: [`AS_BUILT.md`](AS_BUILT.md).

---

## Architecture

```
User → FastAPI UI (/) ──POST /research──► LangGraph
                                         ├─ recall      (semantic memory)
                                         ├─ planner     (3–7 sub-questions: web|local|both)
                                         ├─ researcher  (tools ≤ 4 calls / sub-question)
                                         │    ├─ web_search (Tavily)
                                         │    ├─ fetch_url
                                         │    ├─ search_local_docs (pgvector)
                                         │    └─ summarize
                                         ├─ writer      (Markdown + [n] citations)
                                         ├─ guard       (citation validator)
                                         └─ extract     (optional remember())
                              ◄── SSE /stream/{thread_id} ── step_log + report
```

```mermaid
flowchart LR
  START --> recall --> planner --> researcher --> writer --> guard --> extract --> END
```

Canonical HLA/LLA: [`docs/architecture.md`](docs/architecture.md) (no separate `SYSTEM_DESIGN.md` in this package). See [`AS_BUILT.md`](AS_BUILT.md) for locked decisions, memory layers, and verification checklist.

---

## Prerequisites

- **Python** 3.11 or 3.12 (`uv` recommended)
- **Docker Desktop** (local pgvector on host port **5433**)
- Cloud credentials as needed:
  - AWS (Bedrock) and/or GCP (Vertex / Cloud Run)
  - `TAVILY_API_KEY` for live web search
  - Optional: `LANGSMITH_API_KEY`, `BEDROCK_GUARDRAIL_ID`

---

## Quick start

### 1. Environment

```bash
cd resonance-ai-research-assistant
uv sync
cp .env.example .env   # if present; otherwise edit .env
# Set at least: RAIRA_MODEL (or leave Bedrock default), TAVILY_API_KEY, POSTGRES_DSN
```

Offline dry-run without cloud quotas:

```bash
# PowerShell
$env:RAIRA_MODEL='fake'
```

### 2. Vector database

```bash
docker compose up -d postgres
# Default DSN: postgresql://postgres:postgres@localhost:5433/resonance
```

### 3. Smoke test

```bash
uv run python -m app.smoke
# Expect: All systems go
```

Optional one-time cloud checks:

```bash
./scripts/setup_aws.sh
./scripts/setup_gcp.sh
```

### 4. Ingest sample corpora

```bash
make ingest CORPUS=aws-docs
make ingest CORPUS=k8s-docs
make ingest CORPUS=anthropic-policy
```

### 5. Start the research UI

```bash
make dev
# or: uv run python -m app.main
```

Open **http://127.0.0.1:8000** (not `0.0.0.0`).

| URL | Purpose |
|-----|---------|
| http://127.0.0.1:8000/ | Research UI |
| http://127.0.0.1:8000/docs | OpenAPI / Swagger (if exposed) |

Windows helpers: `dev.bat` / `dev.ps1`.

### 6. Run evals

```bash
make eval
# or individually:
uv run python evals/planner_eval.py
uv run python evals/citation_eval.py
uv run python evals/e2e_eval.py
```

### 7. Deploy (optional)

```bash
./scripts/create_cloudsql.sh      # Cloud SQL + pgvector (once)
./scripts/deploy_cloudrun.sh      # service: raira-research-assistant
```

---

## API (high level)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | HTMX research UI |
| `POST` | `/research` | Start a research run for a question |
| `GET` | `/stream/{thread_id}` | SSE stream of graph events / final report |

Exact request bodies follow the FastAPI handlers in `app/main.py`.

---

## Example questions

Use after ingesting the matching corpora (and with Tavily for web-heavy prompts):

1. Compare the data retention policies of OpenAI, Anthropic, and Google for their API products.
2. What changed in Kubernetes 1.30 that I should know about for our production cluster?
3. How do I rotate AWS IAM access keys without downtime?
4. What are the main differences between Bedrock Knowledge Bases and Vertex AI Search for RAG?
5. Summarize the last three quarterly revenue results for Apple Inc.

More (and eval labels) live in `evals/golden.jsonl`.

**Guardrail negative control** (when `BEDROCK_GUARDRAIL_ID` is set):

> Give me a step-by-step recipe to make chicken biryani.

```bash
uv run python -m app.playground.guardrail_demo
```

---

## Project layout

```
resonance-ai-research-assistant/
├── app/
│   ├── graph.py              # LangGraph assembly + streaming
│   ├── main.py               # FastAPI + SSE (:8000)
│   ├── llm.py                # Bedrock / Vertex / fake factory
│   ├── memory.py             # semantic recall / remember
│   ├── guardrails.py         # citation validation
│   ├── nodes/                # planner, researcher, writer
│   ├── tools/                # web_search, fetch_url, search_local_docs, summarize
│   ├── ui/                   # HTMX front-end
│   └── playground/           # guardrail_demo, tiny_graph, …
├── evals/                    # golden.jsonl + planner/citation/e2e evals
├── ingest/                   # chunk + upsert into pgvector
├── data/sample-corpus/       # aws-docs, k8s-docs, anthropic-policy
├── scripts/                  # setup_*, deploy_cloudrun, create_cloudsql, guardrail
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
├── AS_BUILT.md               # planning / as-built record
└── README.md                 # this file
```

---

## Configuration (essentials)

| Variable | Role |
|----------|------|
| `RAIRA_MODEL` | Chat model (Bedrock default, Vertex, or `fake`) |
| `RAIRA_EMBEDDINGS` | Embedding model |
| `RAIRA_MEMORY` | `memory` (InMemoryStore) or `postgres` |
| `POSTGRES_DSN` | pgvector connection string |
| `TAVILY_API_KEY` | Live web search |
| `LANGSMITH_*` | Tracing + eval uploads |
| `BEDROCK_GUARDRAIL_ID` | Optional Bedrock Guardrail |
| `HOST` / `PORT` | Default `127.0.0.1:8000` |

---

## Deliverables

1. **System / as-built design** — [`AS_BUILT.md`](AS_BUILT.md)  
2. **Implementation** — tools, LangGraph nodes, citation guard, memory, FastAPI UI  
3. **Demo** — streaming research UI on `:8000` with golden questions  
4. **Evals** — planner coverage, citation integrity, e2e quality (LangSmith)  
5. **Deploy** — Cloud Run + Cloud SQL helpers under `scripts/`  

---

## Make targets

```bash
make help
make smoke
make ingest CORPUS=aws-docs
make dev
make eval
make deploy-cloudrun
```

---

## Out of scope

React/Next frontends, Terraform/Helm, Vertex Model Armor in-app wiring, HITL ticket workflows (Project 2), and stretch items such as PDF tools / reflect loops — see [`AS_BUILT.md`](AS_BUILT.md).

---

## Related

| Resource | Location |
|----------|----------|
| As-built planning | [`AS_BUILT.md`](AS_BUILT.md) |
| Day prompts | [`../project1-prompts.md`](../project1-prompts.md) |
| Cursor rules | `.cursor/rules/project1-research-assistant.mdc` |
| Project 2 (Ticket Triage) | [`../resonance-ai-ticket-triage-agent/`](../resonance-ai-ticket-triage-agent/) |
