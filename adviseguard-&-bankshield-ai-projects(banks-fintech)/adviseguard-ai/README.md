# AdviseGuard AI (`adviseguard-ai`)

**Personalized financial advice + fraud detection + customer support** — LangGraph supervisor, hybrid RAG, Neo4j GraphRAG, compliance/risk judges, and human-in-the-loop.

Sibling to [`../bankshield-ai`](../bankshield-ai) inside `10.adviseguard-&-bankshield-ai-projects`.

- **Workers:** intent → retriever → graph → advisor / fraud / support → compliance → risk → synthesizer → HITL → publish  
- **UI:** FastAPI on **port 8004** — `/` customer · `/ops` employee fraud dashboard  
- **Models:** Bedrock / Vertex / `fake` offline  

Design: [`AS_BUILT.md`](AS_BUILT.md) · [`docs/SYSTEM_DESIGN.md`](docs/SYSTEM_DESIGN.md) · [`project-prompts.md`](project-prompts.md)

## Architecture

HLA Mermaid + HITL sequence: [`docs/architecture.md`](docs/architecture.md)

---

## Quick start

Dependencies are locked in `uv.lock` (LangGraph **0.2.x** / LangChain **0.3.x**). Prefer `uv sync` before the steps below.

From the monorepo root (`10.adviseguard-&-bankshield-ai-projects`), enter the package first:

**Git Bash / bash (MINGW64)**

```bash
cd adviseguard-ai
cp -n .env.example .env 2>/dev/null || true
export ADVISEGUARD_MODEL=fake
export ADVISEGUARD_EMBEDDINGS=fake
./.venv/Scripts/python.exe -m scripts.generate_synthetic_fin_data
./.venv/Scripts/python.exe -m app.ingest.pipeline
./.venv/Scripts/python.exe -m app.graph
./.venv/Scripts/python.exe -m app.main           # http://127.0.0.1:8004
```

**PowerShell**

```powershell
cd adviseguard-ai
Copy-Item .env.example .env -ErrorAction SilentlyContinue
$env:ADVISEGUARD_MODEL='fake'; $env:ADVISEGUARD_EMBEDDINGS='fake'
.\.venv\Scripts\python.exe -m scripts.generate_synthetic_fin_data
.\.venv\Scripts\python.exe -m app.ingest.pipeline
.\.venv\Scripts\python.exe -m app.graph
.\.venv\Scripts\python.exe -m app.main
```

| Action | How |
|--------|-----|
| Demo advice | `POST /ask/demo-advice` or UI button |
| Demo fraud | `POST /fraud/demo` or `/ops` |
| Approve HITL | `POST /approve/{thread_id}` |

```bash
python evals/run_all.py
python security/injection_eval.py   # 50 attacks, expect ≥ 95%
```

Optional: `docker compose up -d` for Neo4j `:7688` and Postgres `:5435`.

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
