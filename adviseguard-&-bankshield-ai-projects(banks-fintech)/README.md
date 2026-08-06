# AdviseGuard AI & BankShield AI — Banks / Fintech Agentic Platforms

Portfolio workspace with two sibling LangGraph multi-agent systems for wealth advice and financial-crime investigation. Shared patterns: hybrid RAG + GraphRAG, cross-provider LLM judges, HITL gates, injection evals (≥95%), and dual deploy stubs (Bedrock AgentCore + Vertex AI Agent Engine).

| Project | Role | Port | Docs |
|---------|------|------|------|
| [`bankshield-ai/`](bankshield-ai/) | Financial-crime investigation → HITL → SAR draft | **8003** | [README](bankshield-ai/README.md) · [AS_BUILT](bankshield-ai/AS_BUILT.md) |
| [`adviseguard-ai/`](adviseguard-ai/) | Personalized advice + fraud screening + customer support | **8004** | [README](adviseguard-ai/README.md) · [AS_BUILT](adviseguard-ai/AS_BUILT.md) |

**Relationship:** Siblings only — neither package imports or calls the other at runtime.

Workspace as-built: [AS_BUILT.md](AS_BUILT.md) · Cursor plan: [.cursor/plan.md](.cursor/plan.md)

## Architecture

Portfolio overview: [`docs/architecture.md`](docs/architecture.md) · [BankShield](bankshield-ai/docs/architecture.md) · [AdviseGuard](adviseguard-ai/docs/architecture.md)

---

## Prerequisites

- Python **3.11** or **3.12** (`uv` recommended)
- Optional: Docker for Neo4j / Postgres per package
- Optional: AWS Bedrock / GCP Vertex credentials for cloud models

---

## Quick start — BankShield AI

```powershell
cd bankshield-ai
Copy-Item .env.example .env -ErrorAction SilentlyContinue
$env:BANKSHIELD_MODEL='fake'; $env:BANKSHIELD_EMBEDDINGS='fake'; $env:BANKSHIELD_JUDGE_MODEL='fake'
.\.venv\Scripts\python.exe -m scripts.generate_synthetic_bank_data
.\.venv\Scripts\python.exe -m app.ingest.pipeline
.\.venv\Scripts\python.exe -m app.main
```

Open [http://127.0.0.1:8003](http://127.0.0.1:8003) — demo mule / sanctions cases, approve HITL to publish SAR draft.

---

## Quick start — AdviseGuard AI

```powershell
cd adviseguard-ai
Copy-Item .env.example .env -ErrorAction SilentlyContinue
$env:ADVISEGUARD_MODEL='fake'; $env:ADVISEGUARD_EMBEDDINGS='fake'
.\.venv\Scripts\python.exe -m scripts.generate_synthetic_fin_data
.\.venv\Scripts\python.exe -m app.ingest.pipeline
.\.venv\Scripts\python.exe -m app.main
```

Open [http://127.0.0.1:8004](http://127.0.0.1:8004) — `/` customer · `/ops` employee fraud dashboard.

---

## Quality gates (per project)

```powershell
# BankShield
cd bankshield-ai
$env:BANKSHIELD_MODEL='fake'
.\.venv\Scripts\python.exe evals/run_all.py
.\.venv\Scripts\python.exe security/injection_eval.py

# AdviseGuard
cd ..\adviseguard-ai
$env:ADVISEGUARD_MODEL='fake'
.\.venv\Scripts\python.exe evals/run_all.py
.\.venv\Scripts\python.exe security/injection_eval.py
```

Injection suites must pass **≥ 95%** before promote.

---

## Model configuration

| Project | Primary | Judge |
|---------|---------|-------|
| BankShield | `BANKSHIELD_MODEL` | `BANKSHIELD_JUDGE_MODEL` |
| AdviseGuard | `ADVISEGUARD_MODEL` | `ADVISEGUARD_JUDGE_MODEL` |

Use `fake` for offline/CI. Optional Neo4j/Postgres via each package’s `docker compose up -d`.

---

## Port map

| Service | BankShield | AdviseGuard |
|---------|------------|-------------|
| FastAPI UI | 8003 | 8004 |
| Neo4j Bolt | 7687 | 7688 |
| Postgres | 5434 | 5435 |
