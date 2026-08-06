# As-Built Planning Document

## Project title

**Resonance AI Research Assistant (LangGraph + LangChain + pgvector)**

Lab package name: `raira-lab-starter` (Project 1 — Research Assistant).  
Sibling Project 2 (Ticket Triage) lives in `../RTTA-AI-Multi-Agent-Ticket-Triage/` and is **out of scope** for this document except where deploy scripts delegate.

---

## Purpose

A multi-step agentic research system that:

1. Recalls per-user semantic memory  
2. Plans 3–7 sub-questions (web / local / both)  
3. Researches with tools (Tavily web, URL fetch, local RAG, summarize)  
4. Writes a cited Markdown report  
5. Validates citations against tool findings  
6. Optionally extracts a durable memory fact  

UI: FastAPI + HTMX + SSE at `http://127.0.0.1:8000`.

---

## Locked decisions

| Area | Decision (as built) |
|------|---------------------|
| Framework | LangGraph state machine + LangChain tools/models |
| Chat model (local default) | `bedrock_converse:openai.gpt-oss-120b-1:0` via `RAIRA_MODEL` |
| Chat model (Cloud Run) | `google_vertexai:gemini-2.5-pro` |
| Embeddings (local default) | `bedrock:amazon.titan-embed-text-v2:0` (1024-d) |
| Embeddings (Cloud Run) | `google_vertexai:text-embedding-005` |
| Provider abstraction | `app/llm.py` → `init_chat_model` / `init_embeddings` only |
| Offline / throttle | `RAIRA_MODEL=fake` + optional `RAIRA_ALLOW_FAKE_FALLBACK` |
| Web search | Tavily (`TAVILY_API_KEY`); mocks when fake / no key |
| Local RAG | pgvector Postgres, table `docs`, Docker host port **5433** |
| Checkpointer | `InMemorySaver` (not Sqlite/Postgres checkpointer) |
| Semantic memory | `RAIRA_MEMORY=memory` → `InMemoryStore`; `postgres` → `PostgresStore` |
| Guardrails | Optional Bedrock Guardrail (`BEDROCK_GUARDRAIL_ID`); in-app citation filter |
| Vertex Model Armor | **Not wired** (GCP-side / out of scope) |
| UI stack | FastAPI + HTMX + SSE — **no React/npm** |
| Observability | LangSmith (`LANGSMITH_*`) |
| P1 deploy target | Google Cloud Run (`scripts/deploy_cloudrun.sh`) |
| Secrets | Env / Secret Manager — never hardcoded |

---

## Architecture

### Graph flow (as built)

```
START → recall → planner → researcher → writer → guard → extract → END
```

| Node | Responsibility |
|------|----------------|
| `recall` | Top-3 memories for `user_id` (`("research_user", user_id)`) |
| `planner` | Structured plan: 3–7 sub-questions tagged `web` / `local` / `both` |
| `researcher` | Tool loop; **max 4 tool calls per sub-question**; URL anti-hallucination |
| `writer` | Markdown report with inline `[n]` citations + Sources section |
| `guard` | `validate_citations`; warns / strips URLs not grounded in findings |
| `extract` | LLM decides `worth_remembering`; may `remember()` a fact |

### State (`ResearchState`)

`question`, `sub_questions`, `findings`, `report`, `step_log`, `memories`, `user_id`

### Memory layers

| Layer | Implementation |
|-------|----------------|
| Thread / run | `InMemorySaver` checkpointer |
| Cross-session semantic | `app/memory.py` — `recall` / `remember` |
| Corpus RAG | pgvector via `search_local_docs` |

### Tools

| Tool | File | Notes |
|------|------|-------|
| `web_search` | `app/tools/web_search.py` | Tavily |
| `fetch_url` | `app/tools/fetch_url.py` | ~8k chars, 10s timeout |
| `search_local_docs` | `app/tools/search_local_docs.py` | pgvector `docs` |
| `summarize` | `app/tools/summarize.py` | ~3 sentences |

### Streaming

`stream_research()` → LangGraph `astream_events(..., version="v2")` → SSE to UI.

### HITL

**None** in Project 1. Human-in-the-loop belongs to Project 2.

```mermaid
flowchart LR
  START --> recall
  recall --> planner
  planner --> researcher
  researcher --> writer
  writer --> guard
  guard --> extract
  extract --> END
```

---

## Project layout (as built)

```
RAIRA-AI-Research-Assistant/
├── app/
│   ├── graph.py              # LangGraph assembly + stream_research
│   ├── main.py               # FastAPI + SSE
│   ├── llm.py                # Bedrock / Vertex / fake factory
│   ├── memory.py             # semantic store helpers
│   ├── guardrails.py         # citation validation
│   ├── _fake_llm.py          # offline deterministic model
│   ├── smoke.py / hello_agent.py
│   ├── nodes/                # planner, researcher, writer
│   ├── tools/                # web_search, fetch_url, search_local_docs, summarize
│   ├── ui/                   # index.html, styles.css
│   └── playground/           # guardrail_demo, tiny_graph, demo_embedding
├── evals/
│   ├── golden.jsonl          # 15 demo / eval questions
│   ├── planner_eval.py
│   ├── citation_eval.py
│   ├── e2e_eval.py
│   └── run_all.py
├── ingest/                   # upsert / chunk / search into pgvector
├── data/sample-corpus/       # aws-docs, k8s-docs, anthropic-policy
├── data/support/             # P2 sample data only (not used by P1 graph)
├── scripts/                  # setup_*, deploy_cloudrun, create_cloudsql, guardrail
├── .cursor/rules/            # house + project rules
├── docker-compose.yml        # pgvector on :5433
├── Dockerfile
├── Makefile
├── pyproject.toml
└── AS_BUILT.md               # this document
```

**Not present in this tree (vs early “final state” map):** `app/agents/`, `app/hitl.py`, `app/memory/` package, `deploy/`, `security/` — those are Project 2 / deferred.

---

## Implementation plan (completed)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| Day 0 | `llm.py`, smoke, Docker Postgres, setup scripts | Done |
| Day 1 | `hello_agent.py` | Done |
| Day 2 | Four tools + Tavily / local RAG | Done |
| Day 3 | Nodes + graph + FastAPI UI shell | Done |
| Day 4 | Citation guardrails + planner/citation/e2e evals | Done |
| Day 5 | Recall + extract memory on graph | Done |
| Day 6–8 (P1) | Cloud Run deploy + Cloud SQL helper + Bedrock guardrail scripts | Done |
| Stretch | Reflect loop, PDF tool, Bedrock KB swap for local docs | **Not built** |

---

## Demo query set (for report screenshots)

Use these from `evals/golden.jsonl` (ingest relevant corpora first: `aws-docs`, `k8s-docs`, `anthropic-policy`).

### Primary screenshot set (recommended 5)

1. **Policy compare (web + local)**  
   *Compare data retention policies of OpenAI, Anthropic, and Google for API products.*

2. **Internal ops (local-heavy)**  
   *What changed in Kubernetes 1.30 for our production cluster?*

3. **AWS IAM (local + steps)**  
   *How do I rotate AWS IAM access keys without downtime?*

4. **Cloud RAG compare**  
   *What are the main differences between Bedrock Knowledge Bases and Vertex AI Search for RAG?*

5. **Finance / web**  
   *Summarize the last three quarterly revenue results for Apple Inc.*

### Secondary / stretch screenshots

6. *What are the core requirements of SOX Section 404 for cloud infrastructure?*  
7. *How did the most recent Federal Reserve rate decision affect large-cap tech stocks?*  
8. *What are the key differences between GDPR and CCPA for cross-border data transfers?*  
9. *Can we embed AGPL-licensed code in a commercial SaaS without open-sourcing our product?*  
10. *What obligations does the EU AI Act place on deployers of general-purpose AI systems?*  
11. *What were the most significant ransomware attacks reported in the past year and how did victims respond?*  
12. *How does climate change affect global wheat supply chains and food prices?*  
13. *What are the WHO recommendations on daily screen time for children under 12?*  
14. *What are the essential components of a zero-trust architecture for hybrid cloud?*  
15. *What do the SEC climate disclosure rules require from public companies in 2025?*

### Guardrail demo (negative control)

*Give me a step-by-step recipe to make chicken biryani.*  
→ Expect Bedrock guardrail block when `BEDROCK_GUARDRAIL_ID` is set (`app/playground/guardrail_demo.py`).

### Screenshot checklist

- [ ] UI home / question entry  
- [ ] Streaming step log (planner → researcher tools → writer)  
- [ ] Final report with `[n]` citations and Sources  
- [ ] Citation guard warning (if any hallucinated URL forced)  
- [ ] LangSmith trace for one golden question  
- [ ] Guardrail blocked cooking prompt (optional)

---

## Out of scope (keeps prototype focused)

- React / Next.js / npm frontends  
- Terraform / Helm / full K8s manifests (console + bash only)  
- Vertex Model Armor wiring in application code  
- Real customer CRM / ticketing integrations (Project 2)  
- HITL approval UI (Project 2)  
- Multi-agent supervisor / ticket taxonomy (Project 2)  
- Reflect / critique loops, PDF ingestion tool, Bedrock KB-backed `search_local_docs` (stretch)  
- Production auth / SSO on the research UI  
- Inventing libraries or hardcoding secrets  

---

## Environment (key variables)

| Variable | Role / default |
|----------|----------------|
| `RAIRA_MODEL` | Chat model; default Bedrock gpt-oss-120b; `fake` offline |
| `RAIRA_EMBEDDINGS` | Embeddings; default Titan v2 |
| `RAIRA_MEMORY` | `memory` or `postgres` |
| `POSTGRES_DSN` | `postgresql://postgres:postgres@localhost:5433/resonance` |
| `TAVILY_API_KEY` | Live web search |
| `LANGSMITH_API_KEY` / `LANGSMITH_TRACING` / `LANGSMITH_PROJECT` | Traces + evals |
| `AWS_REGION` | Bedrock region |
| `GCP_PROJECT` / `GCP_LOCATION` / `GCP_BUCKET` | Vertex / deploy |
| `BEDROCK_GUARDRAIL_ID` / `BEDROCK_GUARDRAIL_VERSION` | Optional; version default `DRAFT` |
| `HOST` / `PORT` | Default `127.0.0.1:8000` |

---

## How to run (local)

```bash
uv sync
docker compose up -d postgres
./scripts/setup_aws.sh          # optional
./scripts/setup_gcp.sh          # optional
uv run python -m app.smoke      # expect "All systems go"
make ingest CORPUS=aws-docs
make ingest CORPUS=k8s-docs
make ingest CORPUS=anthropic-policy
make dev                        # http://127.0.0.1:8000
make eval                       # planner + citation + e2e
```

Windows: `dev.bat` / `dev.ps1`, or `.venv\Scripts\python.exe -m app.main`.

---

## Verification checklist

### Smoke / environment

- [ ] `uv sync` succeeds (Python 3.11–3.12)  
- [ ] `docker compose up -d postgres` — pgvector reachable on `:5433`  
- [ ] `uv run python -m app.smoke` prints **All systems go**  
- [ ] With `RAIRA_MODEL=fake`, graph still produces a non-empty report  

### Ingest / RAG

- [ ] `make ingest CORPUS=aws-docs` loads chunks into `docs`  
- [ ] Local-tagged questions cite `internal://` or corpus sources when expected  

### Product path

- [ ] `make dev` serves UI at `http://127.0.0.1:8000`  
- [ ] Demo query #1 streams planner → researcher → writer  
- [ ] Report includes inline `[n]` and a Sources section  
- [ ] Guard node does not leave ungrounded URLs unflagged  

### Guardrails / memory

- [ ] With `BEDROCK_GUARDRAIL_ID` set, cooking prompt is blocked in `guardrail_demo`  
- [ ] Second related question can surface a recalled memory (extract → recall)  

### Evals

- [ ] `uv run python evals/planner_eval.py` uploads / scores against `raira-planner-golden`  
- [ ] `uv run python evals/citation_eval.py` enforces `min_citations`  
- [ ] `uv run python evals/e2e_eval.py` quality ≥ pass threshold (or documents fake-mode limits)  
- [ ] `make eval` / `evals/run_all.py` completes  

### Deploy (optional for report)

- [ ] `scripts/create_cloudsql.sh` (or existing Cloud SQL)  
- [ ] `scripts/deploy_cloudrun.sh` → service `raira-research-assistant` healthy  
- [ ] One Cloud Run invocation returns a cited report  

---

## Evals (as built)

| Script | What it measures | Pass heuristic |
|--------|------------------|----------------|
| `evals/planner_eval.py` | Sub-question coverage vs `expected_sections` | ≥ 0.7 |
| `evals/citation_eval.py` | Unique URLs ≥ `min_citations`; `[n]` ↔ Sources | Per-row rules |
| `evals/e2e_eval.py` | LLM-as-judge report quality 1–5 | ≥ 3.0 |

Golden dataset: `evals/golden.jsonl` (15 rows). LangSmith experiment prefixes: `planner-eval`, citation run, `e2e-eval`.

---

## Deploy (Project 1)

| Script | Target |
|--------|--------|
| `scripts/deploy_cloudrun.sh` | Cloud Run `raira-research-assistant` |
| `scripts/create_cloudsql.sh` | Cloud SQL + pgvector |
| `scripts/create_guardrail.sh` | Bedrock guardrail helpers |

Note: `scripts/deploy_agentcore.sh` / `deploy_vertex_engine.sh` target **Project 2** (sibling repo or missing `deploy/` here) — not part of P1 as-built verification.

---

## As-built deltas vs early prompts

1. Graph includes **`recall` + `extract`**, not only planner → researcher → writer → guard.  
2. Checkpointer is **`InMemorySaver`**, not `SqliteSaver("checkpoints.sqlite")`.  
3. Memory helpers live in **`app/memory.py`**, not `app/memory/`.  
4. Cloud Run packaging lives under **`scripts/`**; no top-level `deploy/` package for P1.  
5. Project 2 agents / HITL / security evals are **not implemented in this folder**.

---

## Related docs

| Doc | Path |
|-----|------|
| Lab README | `README.md` |
| Day prompts (parent) | `../project1-prompts.md` |
| Cursor rules | `.cursor/rules/project1-research-assistant.mdc`, `raira-agent-style.mdc` |
| Eval notes | `evals/README.md` |
| Sample corpora | `data/README.md` |
| Sibling Project 2 | `../RTTA-AI-Multi-Agent-Ticket-Triage/` |

---

*Document type: as-built planning record for Project 1 in `RAIRA-AI-Research-Assistant`. Update this file when locked decisions or graph topology change.*
