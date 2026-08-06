# BankShield AI (`bankshield-ai`)

**Multi-agent financial crime investigation platform** — LangGraph supervisor, hybrid RAG, Neo4j GraphRAG, explainable recommendations, and human-in-the-loop SAR drafting.

Banks generate high false-positive alert volumes. BankShield gathers KYC, transaction, graph, regulatory, and similar-case evidence, then produces an investigator-ready recommendation. It **never** makes the final high-risk decision alone.

- **Orchestration:** LangGraph **supervisor loop** — workers never route to each other
- **Workers:** triage → identity → transaction → graph → regulatory RAG → similar_case_retriever → risk → recommender → grounder → HITL → SAR publish
- **Deep tooling:** wire/ACH, sanctions/AML, mule-network graph
- **Shallow coverage:** card, ATO, APP/BEC, FedNow/RTP synthetic alerts
- **Models:** AWS Bedrock / Google Vertex / `fake` offline
- **UI:** FastAPI investigator console on **port 8003**

Design record: [`AS_BUILT.md`](AS_BUILT.md) · System design: [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md) · Cursor prompts: [`project-prompts.md`](project-prompts.md)

---

## Architecture

HLA Mermaid + HITL sequence: [`docs/architecture.md`](docs/architecture.md)

```
Alert → FastAPI (/investigate | /investigate/demo)
            → LangGraph (SqliteSaver)
                 START → supervisor
                           ├─ triage_router
                           ├─ identity_kyc
                           ├─ transaction_intel
                           ├─ graph_walker
                           ├─ regulatory_rag
                           ├─ similar_case_retriever
                           ├─ risk_scorer
                           ├─ recommender
                           ├─ grounder_judge
                           ├─ hitl            (interrupt)
                           ├─ sar_publisher
                           └─ END
```

**HITL rule:** `risk_band in {high, critical}` or fraud types in `{wire, sanctions, aml, mule}` always interrupt before SAR publish.

---

## Prerequisites

- Python 3.11 or 3.12 (`uv` recommended)
- Local `.env` (copy from `.env.example`)
- Optional: `docker compose up -d` for Neo4j (`:7687`) and Postgres+pgvector (`:5434`)
- Cloud creds optional: AWS Bedrock / GCP Vertex

---

## Quick start

Dependencies are locked in `uv.lock` (LangGraph **0.2.x** / LangChain **0.3.x**). Prefer `uv sync` before the steps below.

From the monorepo root (`10.adviseguard-&-bankshield-ai-projects`), enter the package first:

**Git Bash / bash (MINGW64)**

```bash
cd bankshield-ai
cp -n .env.example .env 2>/dev/null || true
export BANKSHIELD_MODEL=fake
export BANKSHIELD_EMBEDDINGS=fake
export BANKSHIELD_JUDGE_MODEL=fake
./.venv/Scripts/python.exe -m scripts.generate_synthetic_bank_data
./.venv/Scripts/python.exe -m app.ingest.pipeline
./.venv/Scripts/python.exe -m app.graph          # CLI sample
./.venv/Scripts/python.exe -m app.main           # UI http://127.0.0.1:8003
```

**PowerShell**

```powershell
cd bankshield-ai
Copy-Item .env.example .env -ErrorAction SilentlyContinue
$env:BANKSHIELD_MODEL='fake'; $env:BANKSHIELD_EMBEDDINGS='fake'; $env:BANKSHIELD_JUDGE_MODEL='fake'
.\.venv\Scripts\python.exe -m scripts.generate_synthetic_bank_data
.\.venv\Scripts\python.exe -m app.ingest.pipeline
.\.venv\Scripts\python.exe -m app.graph
.\.venv\Scripts\python.exe -m app.main
```

| Action | How |
|--------|-----|
| Demo mule case | Click **Demo Mule** or `POST /investigate/demo` |
| Demo sanctions | `POST /investigate/demo-sanctions` |
| Custom alert | `POST /investigate` with `alert_id` |
| Approve / edit / reject | Pending card → `/approve/{thread_id}` |

```bash
curl -X POST http://127.0.0.1:8003/investigate/demo
curl http://127.0.0.1:8003/pending
curl http://127.0.0.1:8003/alerts
```

### Evals & security

```bash
uv run python evals/run_all.py
uv run python security/injection_eval.py   # expect ≥ 95%
```

---

## Locked stack (summary)

| Layer | Choice |
|-------|--------|
| Agents | LangGraph supervisor |
| RAG | Hybrid dense + BM25 + rerank |
| Graph | Neo4j (JSON fallback) |
| Vectors (local) | Chroma |
| Structured outputs | Pydantic |
| UI | FastAPI investigator console |
| Deploy stubs | AgentCore + Vertex Agent Engine |

---

## Success metrics (demo)

| Metric | Target |
|--------|--------|
| Groundedness | ≥ 0.85 |
| Evidence ID resolution | ≥ 90% |
| Injection suite | ≥ 95% |
| High-risk HITL | 100% |
| Graph tool budget | ≤ 6 |

---

## How to extend via prompts

Paste prompts from [`project-prompts.md`](project-prompts.md) into Cursor Composer in order. When prompts and runtime diverge, **AS_BUILT wins**.

## CI gates

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR:

- `uv sync --frozen --extra dev`
- `ruff check`
- `pytest` (smoke / unit)
- `evals/run_all.py` with `*_MODEL=fake` (if present)
- injection suite ≥ 95% (if present)

Locally: same commands from the package root.

### Roadmap to excellent

- Shared composite action for `uv` + ruff + pytest across sibling packages
- Nightly LangSmith eval runs (non-fake models) on a schedule
- `uv pip audit` / dependency vulnerability gate in CI
