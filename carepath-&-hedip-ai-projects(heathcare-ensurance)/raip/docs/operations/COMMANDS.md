# RAIP terminal commands

Run from the repo root. On this Windows machine **do not use `uv run`** (Desktop `.venv` is Access denied) and **do not use `$env:` in Git Bash**.

Git Bash is shown first. PowerShell equivalents are in each section.

---

## 0. Go to the repo

**Git Bash**

```bash
cd ~/Desktop/reguMed-authoring-platform
```

**PowerShell / cmd**

```bat
cd /d C:\Users\deched\Desktop\reguMed-authoring-platform
```

---

## 1. One-time setup

Do **not** `source .venv/Scripts/activate` and do **not** run `uv sync` (both hit Access denied on this machine).

```bash
deactivate 2>/dev/null || true
unset VIRTUAL_ENV
unset UV_PROJECT_ENVIRONMENT
bash scripts/sync.sh
```

PowerShell:

```powershell
deactivate
Remove-Item Env:VIRTUAL_ENV, Env:UV_PROJECT_ENVIRONMENT -ErrorAction SilentlyContinue
.\scripts\sync.ps1
```

`.env` already sets `RAIP_MODEL=fake`. Demo HITL: `RAIP_HITL=required`. Tests/evals: `RAIP_HITL=evaluate`.

---

## 2. Quality (lint, types, unit tests)

```bash
export RAIP_MODEL=fake
export RAIP_HITL=evaluate
bash scripts/with-python.sh -m ruff check app tests evals security scripts
bash scripts/with-python.sh -m mypy app tests evals security
bash scripts/with-python.sh -m pytest
bash scripts/with-python.sh -m pytest tests/security -q
```

PowerShell:

```powershell
$env:RAIP_MODEL = "fake"
$env:RAIP_HITL = "evaluate"
.\scripts\with-python.ps1 -m ruff check app tests evals security scripts
.\scripts\with-python.ps1 -m mypy app tests evals security
.\scripts\with-python.ps1 -m pytest
.\scripts\with-python.ps1 -m pytest tests/security -q
```

---

## 3. Golden evals and injection suite

```bash
export RAIP_MODEL=fake
export RAIP_HITL=evaluate
bash scripts/with-python.sh -m evals.run_all
bash scripts/with-python.sh -m security.injection_eval
```

Reports: `evals/reports/latest.json`, `security/reports/injection.json`. Injection gate: ≥ 95%.

PowerShell: same modules via `.\scripts\with-python.ps1`.

---

## 4. Run the console (API + UI)

**cmd / double-click:** `run.bat`

**Git Bash**

```bash
export RAIP_MODEL=fake
export RAIP_HITL=required
bash scripts/run.sh
```

**PowerShell**

```powershell
$env:RAIP_MODEL = "fake"
$env:RAIP_HITL = "required"
.\scripts\run.ps1
```

Open http://127.0.0.1:8011 — demo seed runs on startup. Stop with Ctrl+C.

If the port is in use: close the existing process first.

---

## 5. Health and API checks (second terminal)

```bash
curl.exe -s http://127.0.0.1:8011/health
curl.exe -s http://127.0.0.1:8011/ready
curl.exe -s http://127.0.0.1:8011/metrics
curl.exe -s http://127.0.0.1:8011/projects
curl.exe -s http://127.0.0.1:8011/evaluations
```

OpenAPI: http://127.0.0.1:8011/docs

---

## 6. Optional worker and re-seed

Ingest also runs in-process on upload. Separate worker:

```bash
bash scripts/with-python.sh -m app.worker
```

Re-seed (idempotent if chunks exist):

```bash
bash scripts/with-python.sh -m scripts.seed_demo
```

LangGraph smoke (no HTTP):

```bash
export RAIP_HITL=evaluate
bash scripts/with-python.sh -m app.orchestration.graph
```

---

## 7. Docker (Postgres + Neo4j + API + worker)

```bash
docker compose up --build
docker compose up -d --build
docker compose ps
docker compose logs -f api
docker compose down
```

---

## 8. Full local gate (same as CI intent)

```bash
export RAIP_MODEL=fake
export RAIP_HITL=evaluate
bash scripts/with-python.sh -m ruff check app tests evals security scripts
bash scripts/with-python.sh -m mypy app tests evals security
bash scripts/with-python.sh -m pytest
bash scripts/with-python.sh -m evals.run_all
bash scripts/with-python.sh -m security.injection_eval
bash scripts/with-python.sh -m pytest tests/security -q
```

Do **not** copy CI’s `uv run …` onto this Desktop checkout.

---

## Makefile (Git Bash)

```bash
make sync
make lint
make typecheck
make test
make evals
make inject
make seed
make run
make compose
```
