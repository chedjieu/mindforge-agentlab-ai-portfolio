# Walmart Associate Intelligence Platform (WAIP)

AI-powered **multi-agent** enterprise assistant for 2M+ Walmart associates.

Master LangGraph orchestrator → parallel HR / Payroll / Benefits / Leave / Ticket / Search workers → hybrid GraphRAG (BM25 + vectors + Neo4j) → Compliance + Response Validator judges → HITL-gated ServiceNow actions.

Dual deploy: **Bedrock AgentCore** + **Vertex AI Agent Engine**.

## Quick start

```powershell
cd "C:\Users\deched\projects(ml-ai)\mindforge-agentlab-ai-portfolio\6.waip-&-widra-&-woka-ai-projects(walmart)\waip"
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
uv sync --python 3.12
$env:WAIP_MODEL = "fake"
uv run python -m app.graph
uv run python -m app.main
```

Open [http://127.0.0.1:8004](http://127.0.0.1:8004)

## Quality gates

```powershell
$env:WAIP_MODEL = "fake"
uv run python evals/run_all.py
uv run python security/injection_eval.py
```

Injection suite must pass **≥ 95%**.

## Architecture (short)

See [AS_BUILT.md](AS_BUILT.md), [docs/architecture.md](docs/architecture.md), [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md).

| Layer | Tech |
|-------|------|
| Orchestration | LangGraph master + parallel `Send` |
| RAG | Hybrid BM25 + dense + Neo4j GraphRAG + rerank |
| Memory | Procedural / episodic / semantic |
| Models | Bedrock / Vertex via gateway (`WAIP_MODEL`) |
| Tools | MCP-shaped Workday / ServiceNow / Leave / SAP mocks |
| Safety | Firewall + judges + HITL + 50-attack suite |
| Observability | LangSmith-ready evals, audit JSONL |
| Infra sketch | `infra/compose/docker-compose.yml` |

## Golden demo query

> My paycheck is short because I took medical leave last week. Can you explain why and open a payroll ticket if necessary?

Approve the HITL card to create a mock `INC*` ticket.

## Cloud models (optional)

```powershell
$env:WAIP_MODEL = "bedrock_converse:anthropic.claude-3-5-sonnet-20241022-v2:0"
# or
$env:WAIP_MODEL = "google_vertexai:gemini-2.5-pro"
```

## Deploy adapters

```powershell
uv run python deploy/agentcore/entrypoint.py
uv run python deploy/vertex_engine/entrypoint.py
```

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
