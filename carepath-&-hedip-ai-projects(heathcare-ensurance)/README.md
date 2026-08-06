# CarePath AI & HEDIP — Healthcare / Insurance Agentic Platforms

> **Folder note:** This workspace directory is named `heathcare-ensurance` (typo). The intended domain spelling is **healthcare / insurance**.

Portfolio workspace with two sibling LangGraph multi-agent systems for clinical and payer decision workflows. Shared patterns: hybrid RAG + GraphRAG, three memory layers, cross-provider LLM judges, HITL gates, injection evals (≥95%), and dual deploy (Bedrock AgentCore + Vertex AI Agent Engine).

| Project | Role | Port | Docs |
|---------|------|------|------|
| [`carepath-ai/`](carepath-ai/) | Personalized treatment plan generation (clinical CDS) | **8007** | [README](carepath-ai/README.md) · [Architecture](carepath-ai/docs/architecture.md) · [AS_BUILT](carepath-ai/AS_BUILT.md) |
| [`hedip/`](hedip/) | Enterprise Healthcare Decision Intelligence Platform (multi-domain) | **8009** | [README](hedip/README.md) · [Architecture](hedip/docs/architecture.md) · [AS_BUILT](hedip/AS_BUILT.md) |

**Relationship:** CarePath remains standalone. HEDIP reimplements clinical CDS as one domain and does **not** depend on `carepath-ai` at runtime.

Workspace as-built: [AS_BUILT.md](AS_BUILT.md).

---

## Prerequisites

- Python **3.12**
- [uv](https://github.com/astral-sh/uv) on `PATH`
- Optional: Neo4j (`NEO4J_URI`), Postgres checkpointer (`POSTGRES_DSN`), AWS/GCP credentials for cloud models

---

## Quick start — CarePath AI

```powershell
cd carepath-ai
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
uv sync --python 3.12
$env:CAREPATH_MODEL = "fake"
uv run python -m app.graph
uv run python -m app.main
```

Open [http://127.0.0.1:8007](http://127.0.0.1:8007)

**Golden demo:** patient **P001** (T2DM + HTN + 6 meds); prefer non-injectable pathway; approve HITL to publish.

---

## Quick start — HEDIP

```powershell
cd hedip
$env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
uv sync --python 3.12
$env:HEDIP_MODEL = "fake"
uv run python -m app.graph
uv run python -m app.main
```

Open [http://127.0.0.1:8009](http://127.0.0.1:8009)

Domains: prior auth, claims denial prevention, clinical CDS, care coordination, knowledge Q&A, fraud scoring, population health, RCM coding assist.

---

## Quality gates (per project)

```powershell
# CarePath
cd carepath-ai
$env:CAREPATH_MODEL = "fake"
uv run python -m evals.run_all
uv run python -m security.injection_eval

# HEDIP
cd ..\hedip
$env:HEDIP_MODEL = "fake"
uv run python -m evals.run_all
uv run python -m security.injection_eval
```

Injection suites must pass **≥ 95%** before promote.

---

## Model configuration

| Project | Primary | Judge |
|---------|---------|-------|
| CarePath | `CAREPATH_MODEL` | `CAREPATH_JUDGE_MODEL` |
| HEDIP | `HEDIP_MODEL` | `HEDIP_JUDGE_MODEL` |

Use `fake` for offline/CI. Cloud examples:

```powershell
$env:CAREPATH_MODEL = "bedrock_converse:anthropic.claude-3-5-sonnet-20241022-v2:0"
$env:CAREPATH_JUDGE_MODEL = "google_vertexai:gemini-2.5-pro"
# same pattern with HEDIP_* for hedip
```

---

## Layout

```
.
├── README.md                 # this file
├── AS_BUILT.md               # workspace as-built
├── carepath-ai/              # clinical treatment-plan platform
│   ├── README.md
│   ├── AS_BUILT.md
│   └── docs/
└── hedip/                    # multi-domain decision intelligence platform
    ├── README.md
    ├── AS_BUILT.md
    └── docs/
```

---

## Explicitly not v1

Live FHIR/EHR, real CMS/PBM APIs, Kafka-in-request-path, SSO/IdP, and HIPAA production hardening are out of scope for both packages.
