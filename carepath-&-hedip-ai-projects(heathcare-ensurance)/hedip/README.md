# HEDIP — Healthcare Decision Intelligence Platform

**Enterprise Healthcare Decision Intelligence Platform Using Agentic AI, GraphRAG, and Multi-Agent Reasoning**

Multi-domain LangGraph platform: prior auth, claims denial prevention, clinical CDS, care coordination, knowledge Q&A, fraud scoring, population health, and RCM coding assist.

## Quick start

```powershell
cd "c:\Users\deched\projects(ml-ai)\0.ide_vs-code_&_cursor\10.healthcare-insurance\hedip"
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
uv sync --python 3.12
$env:HEDIP_MODEL = "fake"
uv run python -m app.graph
uv run python -m app.main
```

Open [http://127.0.0.1:8009](http://127.0.0.1:8009)

## Quality gates

```powershell
$env:HEDIP_MODEL = "fake"
uv run python -m evals.run_all
uv run python -m security.injection_eval
```

## Docs

[AS_BUILT.md](AS_BUILT.md) · [docs/architecture.md](docs/architecture.md) · [docs/SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)

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
