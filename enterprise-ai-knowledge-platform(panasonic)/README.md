# Panasonic Enterprise GenAI Knowledge Platform (`panasonic-egkp`)

**Production-oriented RAG + knowledge-graph multi-agent system** for enterprise knowledge Q&A across engineering, manufacturing, HR, operations, and customer support — designed after the Panasonic-scale platform narrative (2,000+ internal users, hybrid retrieval, citations, RBAC).

Incoming questions are classified by intent/domain, retrieved via hybrid search, expanded through a knowledge graph when relationships matter, drafted with citations (three memory layers), grounded by a claim–evidence checker, paused for **human-in-the-loop** on sensitive domains, then published.

- **Orchestration:** LangGraph **supervisor loop** — workers never route to each other
- **Workers:** `intent_router` → `retriever` → `graph_walker` → `synthesizer` → `grounder` → `hitl` → `answer_publish`
- **Memory:** procedural (versioned prompts) · episodic (similar past Q&A) · semantic (per-user/role Store)
- **Knowledge graph:** Neo4j GraphRAG (part ↔ SOP ↔ plant ↔ policy)
- **Models:** AWS Bedrock (`gpt-oss-120b`) or Google Vertex (`gemini-2.5-pro`); `fake` for offline demos
- **Judge:** cross-provider LLM-as-judge with verbosity / position / same-model bias mitigations
- **UI:** FastAPI approval console on **port 8002**
- **Deploy:** Bedrock AgentCore **and** Vertex AI Agent Engine
- **Quality / safety:** LangSmith evals + deploy gates + 20-attack injection suite (pass ≥ 95%)

Design record: [`AS_BUILT.md`](AS_BUILT.md) · Architecture (canonical HLA/LLA): [`docs/architecture.md`](docs/architecture.md) · System design: [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md) · Cursor prompts: [`project-prompts.md`](project-prompts.md)

---

## Architecture

Canonical diagrams (HLA Mermaid + supervisor/HITL sequence): **[`docs/architecture.md`](docs/architecture.md)**.

ASCII sketch of the ask path:

```
Query → FastAPI (/ask | /ask/demo)
            → LangGraph (SqliteSaver locally)
                 START → supervisor
                           ├─ intent_router     domain + intent + sensitivity
                           ├─ retriever         hybrid dense + BM25 + metadata + rerank
                           ├─ graph_walker      Neo4j hops (≤ 6 tool calls)
                           ├─ synthesizer       answer + citations (3 memory layers)
                           ├─ grounder          claim–evidence score; may force revise
                           ├─ hitl              interrupt → approve | edit | reject
                           ├─ answer_publish    mock publish log
                           └─ END
            ← Approval UI polls /pending → POST /approve/{thread_id}
```

**Routing (pure logic, no LLM):** missing intent → router; empty chunks → retriever; needs relationships → graph walker; no draft → synthesizer; no grounding → grounder; sensitive/low-confidence → HITL; approved → publish.

**Security:** hard-block prompt-injection patterns (and optional Bedrock Guardrail) refuse before retrieval; softer risk/PII cases escalate through grounder + HITL.

---

## Target metrics (demo-measurable)

| Metric | Target |
|--------|--------|
| Retrieval relevance lift | ≥ 40% vs naive chunking baseline |
| P50 / P95 latency | ≤ 2s / ≤ 4s for standard Q&A |
| Groundedness (judge) | ≥ 0.85 pass rate to ship |
| Citation coverage | ≥ 90% of claims cite a source |
| Injection suite | ≥ 95% blocked/escalated |
| Availability | 99.9% design target |

---

## Prerequisites

- **Python** 3.11 or 3.12 (`uv` recommended)
- Local **`.env`** (or shared env from a sibling starter repo)
- Optional: Docker Postgres on `:5433` for Store / episodic pgvector
- Optional: Docker Neo4j on `:7687` for GraphRAG
- Cloud creds as needed: AWS (Bedrock / AgentCore), GCP (Vertex / Agent Engine)
- Optional: `LANGSMITH_API_KEY`, `SLACK_BOT_TOKEN`, `BEDROCK_KB_ID`, `BEDROCK_GUARDRAIL_ID`

---

## Quick start (after implementing via prompts)

```bash
cd panasonic-egkp   # or this repo root once scaffolded
uv sync

# Offline dry-run
# PowerShell: $env:EGKP_MODEL='fake'

uv run python -m scripts.generate_synthetic_corpus
uv run python -m app.ingest.pipeline
uv run python -m app.graph          # CLI sample query
uv run python -m app.main           # UI http://127.0.0.1:8002
```

| Action | How |
|--------|-----|
| Demo query | Click **Demo** or `POST /ask/demo` |
| Custom query | `POST /ask` with JSON body |
| Approve / edit / reject | Pending card → `/approve/{thread_id}` |

```bash
curl -X POST http://127.0.0.1:8002/ask/demo
curl http://127.0.0.1:8002/pending
```

### Evals & security

```bash
uv run python evals/retrieval_judge.py
uv run python evals/groundedness_judge.py
uv run python evals/answer_quality_judge.py
uv run python evals/pairwise_regression.py
uv run python evals/e2e_eval.py
uv run python evals/run_all.py

uv run python security/injection_eval.py   # expect ≥ 95%
```

---

## How to build this project

This repo ships **design docs + a Cursor Composer prompt library**. Implementation follows the same day-ordered workflow as Monk Project 2:

1. Open this folder in Cursor.
2. Paste prompts from [`project-prompts.md`](project-prompts.md) into Composer in order (`Day 1 H1` → … → Bonus).
3. Keep [`AS_BUILT.md`](AS_BUILT.md) locked decisions as the source of truth when prompts and runtime diverge.

---

## Corpus (demo, NDA-safe)

Synthetic + license-clear public excerpts under `data/corpus/{domain}/`, with aligned KG seeds in `data/kg/`. See [Corpus & KG schema](docs/SYSTEM_DESIGN.md#corpus--knowledge-graph-schema) in the system design doc.

| Domain | Content |
|--------|---------|
| `manufacturing` | Plant SOPs, machine safety procedures |
| `engineering` | Design standards, supersession chains |
| `support` | Product KB, troubleshooting trees |
| `hr` | Handbook policies (HITL required) |
| `operations` | ITIL-style incident/change runbooks |

---

## Locked stack (summary)

| Layer | Choice |
|-------|--------|
| Agents | LangGraph supervisor (not CrewAI / AutoGen / Strands) |
| RAG | LangChain + hybrid fusion + rerank |
| Graph | Neo4j |
| Vectors (local) | Chroma + optional pgvector |
| Vectors (AWS / GCP) | OpenSearch or Bedrock KB / Vertex Vector Search or AlloyDB |
| Ingestion orchestration | Step Functions / Cloud Workflows (not chat loop) |
| Deploy | AgentCore + Vertex Agent Engine |

### Bedrock AgentCore

```bash
# Requires POSTGRES_DSN + AWS creds. Managed AgentCore memory stays OFF by default.
export DISABLE_AGENTCORE_MEMORY=1
bash deploy/deploy_agentcore.sh
```

Entrypoint: root [`agentcore_entrypoint.py`](agentcore_entrypoint.py) (re-exported from `deploy/` for the Day 3 prompt path). Uses `build_graph_with_backends(PostgresSaver, PostgresStore)`.

### Vertex AI Agent Engine

```bash
# Requires GCP_PROJECT, GCP_BUCKET (+ gcloud ADC). Writes .env.deployed
bash deploy/deploy_vertex_engine.sh
```

Deploys `agent_engines.LanggraphAgent` wrapping `build_graph()` as `panasonic-egkp`.

---

## CI gates

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR:

- `uv sync --frozen --extra dev`
- `ruff check`
- `pytest` (smoke / unit)
- `evals/run_all.py` with `EGKP_MODEL=fake`
- injection suite ≥ 95% (`security/injection_eval.py`)

Locally: same commands from the package root.

Docker: `docker compose up --build` (API on `:8002`, health at `/health`). Optional Neo4j: `docker compose --profile neo4j up --build`.

### Roadmap to excellent

- Shared composite action for `uv` + ruff + pytest across sibling packages
- Nightly LangSmith eval runs (non-fake models) on a schedule
- `uv pip audit` / dependency vulnerability gate in CI

---

## Related docs

| Doc | Path |
|-----|------|
| As-built / locked decisions | [`AS_BUILT.md`](AS_BUILT.md) |
| Architecture (HLA/LLA) | [`docs/architecture.md`](docs/architecture.md) |
| System design | [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md) |
| Cursor prompt library | [`project-prompts.md`](project-prompts.md) |
| Reference Project 2 | `../3.mt_agentic_ai/starter-repo-main/monk-ticket-triage/` |
| Reference prompts | `../3.mt_agentic_ai/starter-repo-main/project2-prompts.md` |
