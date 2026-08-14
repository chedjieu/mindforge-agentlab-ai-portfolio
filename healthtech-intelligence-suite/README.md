# HealthTech Intelligence Suite

An integrated enterprise ecosystem for AI-driven patient care navigation, quality measure performance tracking, and risk adjustment analytics.

The three packages are **sister projects** — shared LangGraph / GraphRAG / HITL patterns, **no runtime imports** across packages.

| Project | Domain | Port | Docs |
| :--- | :--- | ---: | :--- |
| **[CarePath AI](./carepath-ai)** | Care pathways and clinical decision support | **8007** | [README](carepath-ai/README.md) · [AS_BUILT](carepath-ai/AS_BUILT.md) · [System design](carepath-ai/docs/SYSTEM_DESIGN.md) |
| **[HEDI Platform](./hedip)** | Quality / HEDIS-oriented decision intelligence | **8009** | [README](hedip/README.md) · [AS_BUILT](hedip/AS_BUILT.md) · [System design](hedip/docs/SYSTEM_DESIGN.md) |
| **[RAIP Engine](./raip)** | **RAIP Engine — ReguMed Authoring Intelligence Platform** | **8011** | [README](raip/README.md) · [AS_BUILT](raip/AS_BUILT.md) · [System design](raip/docs/SYSTEM_DESIGN.md) · [Implementation plan](raip/docs/IMPLEMENTATION_PLAN.md) |

**How they relate:** CarePath produces a defensible care pathway. HEDIP evaluates quality, utilization, and payer/provider decisions for the same member population. RAIP grounds the documentation and coding narrative in approved sources so quality and risk-adjustment artifacts can be cited and audited. None of the three calls another at runtime.

Workspace as-built: [AS_BUILT.md](AS_BUILT.md).

---

## CarePath AI

Personalized treatment-plan generation for complex chronic-care patients. LangGraph supervisor → extract → medication check → plan → preferences → safety judge → HITL publish.

```powershell
cd carepath-ai
uv sync --python 3.12
$env:CAREPATH_MODEL = "fake"
uv run python -m app.main
```

Open [http://127.0.0.1:8007](http://127.0.0.1:8007) — golden patient **P001** (T2DM + HTN + 6 meds).

---

## HEDI Platform

Umbrella healthcare decision intelligence: prior auth, claims, clinical CDS, care coordination, knowledge Q&A, fraud, population health, and RCM coding assist. Quality / HEDIS performance is the suite thesis on the pop-health, claims, RCM, and knowledge domains.

```powershell
cd hedip
uv sync --python 3.12
$env:HEDIP_MODEL = "fake"
uv run python -m app.main
```

Open [http://127.0.0.1:8009](http://127.0.0.1:8009)

---

## RAIP Engine

Evidence-grounded clinical/regulatory and risk-adjustment authoring with claim-level provenance, citation validation, HCC/RAF-ready workflows, and publication blocking for unsupported claims.

```bash
cd raip
bash scripts/sync.sh
bash scripts/run.sh
```

Open [http://127.0.0.1:8011](http://127.0.0.1:8011)

---

## Workspace setup

```bash
git clone --recursive <repository-url> mindforge-agentlab-ai-portfolio
cd mindforge-agentlab-ai-portfolio/healthtech-intelligence-suite
```

**Prerequisites:** Python **3.12**, [uv](https://github.com/astral-sh/uv) on `PATH`. Optional: Docker Desktop, AWS/GCP credentials (otherwise use `*_MODEL=fake`).

### Docker (all three stacks)

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

## Quality gates

From this directory, a model env var selects the sister project (`RAIP_MODEL` → `raip/`, `CAREPATH_MODEL` → `carepath-ai/`, `HEDIP_MODEL` → `hedip/`). If none is set, all three run.

```powershell
$env:RAIP_MODEL = "fake"
.\scripts\with-python.ps1 -m pytest
.\scripts\with-python.ps1 -m evals.run_all
.\scripts\with-python.ps1 -m security.injection_eval
```

On Windows, `uv run` often cannot spawn `*\Scripts\python.exe` (Access is denied). Use `scripts/with-python.ps1` as above, or `cd` into a package. Injection suites must pass **≥ 95%** before promote.

## Layout

```text
healthtech-intelligence-suite/
├── carepath-ai/
├── hedip/
├── raip/
├── docker-compose.yml
├── AS_BUILT.md
└── README.md
```

## Explicitly not v1

Live FHIR/EHR, real CMS/PBM APIs, production RAF/HCC calculators, Kafka-in-request-path, SSO/IdP, and HIPAA production hardening are out of scope. Sample data is synthetic. This suite is **not** a HIPAA certification.
