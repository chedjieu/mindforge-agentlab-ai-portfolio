# Agentic RAG Chatbot (LangChain + n8n)

AI Research Knowledge Assistant grounded in [Lilian Weng](https://lilianweng.github.io/) blog posts.  
LangChain handles retrieval and tool-calling; ChromaDB stores embeddings; n8n provides the chat UI, logging, and optional Slack/webhook alerts.

## Architecture

```
User → n8n Chat UI → n8n Workflow → FastAPI (/chat)
                                      → LangChain Agent
                                         → ChromaDB (RAG)
                                         → Web search (optional)
                                      → JSONL logs
```

Canonical HLA/LLA: [docs/architecture.md](docs/architecture.md). Full design: [docs/system_design.md](docs/system_design.md).

## Prerequisites

- Python **3.11 or 3.12** (see `pyproject.toml` / `uv.lock`)
- [uv](https://github.com/astral-sh/uv) recommended (or pip + `requirements.txt`)
- Docker Desktop (for n8n)
- OpenAI API key

## Quick start

### 1. Python environment

```bash
# Preferred (locked):
uv sync
cp .env.example .env
# Edit .env and set OPENAI_API_KEY

# Or with pip:
python -m venv .venv
#   Git Bash:    source .venv/Scripts/activate
#   PowerShell:  .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Ingest the knowledge base

```bash
python -m src.ingest
```

This fetches the 20 URLs in `data/urls.txt`, chunks them, embeds with `text-embedding-3-small`, and persists to `data/chroma/`.

### 3. Start the API

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` means “listen on all interfaces” so n8n/Docker can reach the API.  
**In a browser, open `http://localhost:8000` (or `http://127.0.0.1:8000`) — not `http://0.0.0.0:8000`.**

Useful URLs:

- Home (redirects to docs): http://localhost:8000/  
- Health: http://localhost:8000/health  
- Swagger UI: http://localhost:8000/docs  
- n8n Chat UI: http://localhost:5678/  


Check health from the terminal:

```bash
curl http://localhost:8000/health
```

Example chat:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"What causes extrinsic hallucinations in LLMs?\", \"session_id\": \"demo\"}"
```

### 4. Start n8n (Docker)

```bash
docker compose up -d
```

Open http://localhost:5678

1. Create an owner account (first launch).
2. **Workflows → Import from File** → select `n8n/workflows/agentic_rag_chatbot.json`.
3. Activate the workflow.
4. Open the **Chat** trigger panel (or the public chat URL shown on the Chat Trigger node).

The workflow calls `http://host.docker.internal:8000/chat` so the container can reach the API on your host machine.

### 5. Optional Slack / webhook alerts

In the imported workflow, configure the **Slack / Webhook** node with your webhook URL (or set `SLACK_WEBHOOK_URL` and wire it into the HTTP Request node). Alerts fire when the user message contains `escalate` or `human`, or when the API returns an error.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Service + KB document count |
| `POST` | `/chat` | `{ "message", "session_id?" }` → answer, sources, tool steps |
| `POST` | `/ingest` | Re-run the ingestion pipeline |

## Example questions

- What causes extrinsic hallucinations in LLMs?
- Summarize LLM-powered autonomous agents.
- How do diffusion models generate video?
- Compare prompt engineering techniques from the posts.
- What’s the weather in Toronto? *(out-of-KB — should use web search or refuse)*

## Project layout

```
├── data/urls.txt
├── docs/architecture.md
├── docs/system_design.md
├── docs/final_report.md
├── n8n/workflows/agentic_rag_chatbot.json
├── src/
│   ├── ingest.py
│   ├── config.py
│   ├── rag/
│   ├── agent/
│   └── api/main.py
├── docker-compose.yml
└── requirements.txt
```

## Deliverables

1. **Architecture** — [docs/architecture.md](docs/architecture.md) · **System design** — [docs/system_design.md](docs/system_design.md)
2. **Implementation** — ingestion, RAG, agent tools, n8n workflow
3. **Demo chatbot** — n8n Chat Trigger interface
4. **Final report** — [docs/final_report.md](docs/final_report.md)

**Planning (as built):** [AS_BUILT.md](AS_BUILT.md) — locked decisions, architecture, layout, implementation plan, demo queries, out of scope, verification checklist.
