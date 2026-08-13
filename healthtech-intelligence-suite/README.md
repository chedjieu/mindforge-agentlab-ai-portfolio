# HealthTech Intelligence Suite

An integrated enterprise ecosystem for AI-driven patient care navigation, quality measure performance tracking, and risk adjustment analytics.

**Portfolio path:** [`healthtech-intelligence-suite/`](../healthtech-intelligence-suite/) — public GitHub tree with no `&` in the URL so CarePath, HEDIP, and RAIP are all browsable.

The three packages are **sister projects** — shared LangGraph / GraphRAG / HITL patterns, **no runtime imports** across packages.

Execution plans: [`.cursor/plan-overview.md`](.cursor/plan-overview.md) · [plan-carepath-ai.md](.cursor/plan-carepath-ai.md) · [plan-hedip.md](.cursor/plan-hedip.md) · [plan-raip.md](.cursor/plan-raip.md).

## Sister projects

| Project | Domain | Key capabilities | Port |
| :--- | :--- | :--- | ---: |
| **[CarePath AI](./carepath-ai)** | Clinical AI and care pathways | AI-guided care plans, patient navigation, clinician HITL, medication-safety checks | **8007** |
| **[HEDI Platform](./hedip)** | HEDIS and quality metrics | Healthcare Effectiveness Data and Information performance tracking, prior auth, claims, population risk, coding assist | **8009** |
| **[RAIP Engine](./raip)** | Risk adjustment and incentives | Evidence-grounded documentation, claim-level provenance, HCC/RAF-ready authoring path, publication blocking on unsupported claims | **8011** |

**How they relate:** CarePath produces a defensible care pathway. HEDIP evaluates quality, utilization, and payer/provider decisions for the same member population. RAIP grounds the documentation and coding narrative in approved sources so quality and risk-adjustment artifacts can be cited and audited. None of the three calls another at runtime.

Workspace as-built: [AS_BUILT.md](AS_BUILT.md).

## Workspace setup

```bash
git clone --recursive <repository-url> mindforge-agentlab-ai-portfolio
cd mindforge-agentlab-ai-portfolio/healthtech-intelligence-suite
```

**Prerequisites**

- Python **3.12** and [uv](https://github.com/astral-sh/uv) on `PATH`
- Optional: Docker Desktop for shared Neo4j / Postgres (`docker compose up -d`)
- Optional: AWS/GCP credentials for Bedrock / Vertex (otherwise use `*_MODEL=fake`)

### Docker (all three stacks)

From this directory:

```bash
docker compose up -d
docker compose ps
```

| Stack | Postgres | Neo4j HTTP / Bolt |
|-------|----------|-------------------|
| CarePath | 5435 | 7475 / 7688 |
| HEDIP | 5436 | 7476 / 7689 |
| RAIP | 5432 | 7474 / 7687 |

CarePath and HEDIP apps still run with `uv`. RAIP's compose stack also builds API (`8011`) and worker.

### Quick start — CarePath AI

```powershell
cd carepath-ai
uv sync --python 3.12
$env:CAREPATH_MODEL = "fake"
uv run python -m app.main
```

Open [http://127.0.0.1:8007](http://127.0.0.1:8007) — golden patient **P001**.

### Quick start — HEDI Platform

```powershell
cd hedip
uv sync --python 3.12
$env:HEDIP_MODEL = "fake"
uv run python -m app.main
```

Open [http://127.0.0.1:8009](http://127.0.0.1:8009)

### Quick start — RAIP Engine

```bash
cd raip
bash scripts/sync.sh
bash scripts/run.sh
```

Open [http://127.0.0.1:8011](http://127.0.0.1:8011)

## Quality gates

From this directory, with a model env var set, the same commands the packages use are forwarded into that sister project (`RAIP_MODEL` → `raip/`, `CAREPATH_MODEL` → `carepath-ai/`, `HEDIP_MODEL` → `hedip/`). If none is set, all three run.

```powershell
$env:RAIP_MODEL = "fake"
uv sync --python 3.12
uv run pytest
uv run python -m evals.run_all
uv run python -m security.injection_eval
```

On this Windows machine `uv run` often cannot spawn `*\Scripts\python.exe` (Access is denied). Use the uv-managed interpreter instead:

```powershell
$env:RAIP_MODEL = "fake"
.\scripts\with-python.ps1 -m pytest
.\scripts\with-python.ps1 -m evals.run_all
.\scripts\with-python.ps1 -m security.injection_eval
```

Or `cd` into `carepath-ai`, `hedip`, or `raip` and run the package commands there. Injection suites must pass **≥ 95%** before promote.

## Layout

```text
healthtech-intelligence-suite/
├── .cursor/                  # suite execution plans
├── carepath-ai/              # CarePath AI
├── hedip/                    # HEDI Platform
├── raip/                     # RAIP Engine
├── docker-compose.yml        # shared local infra
├── .gitignore
├── AS_BUILT.md
└── README.md
```

## Explicitly not v1

Live FHIR/EHR, real CMS/PBM APIs, production RAF/HCC calculators, Kafka-in-request-path, SSO/IdP, and HIPAA production hardening are out of scope. Sample data is synthetic. This suite is **not** a HIPAA certification.
