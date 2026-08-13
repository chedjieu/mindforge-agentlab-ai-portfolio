# HealthTech Intelligence Suite — Overview Plan

**Canonical parent:** `healthtech-intelligence-suite/`  
**Sister projects:** `carepath-ai` · `hedip` · `raip`  
**Portfolio:** MindForge AgentLab (healthcare / insurance vertical)

An integrated enterprise ecosystem for AI-driven patient care navigation, quality measure performance tracking, and risk-adjustment analytics. The three packages are **sister products**: shared engineering patterns, isolated runtimes, no cross-imports.

| Project | Product name | Suite role | As-built runtime | Port |
|---------|--------------|------------|------------------|------|
| [`carepath-ai`](../carepath-ai/README.md) | CarePath AI | Care pathways and clinical CDS | Personalized treatment-plan generation | **8007** |
| [`hedip`](../hedip/README.md) | HEDI Platform | Quality / HEDIS-oriented performance engine | Multi-domain healthcare decision intelligence | **8009** |
| [`raip`](../raip/README.md) | RAIP Engine | Risk adjustment and quality-incentive processing | Evidence-first clinical/regulatory authoring (ReguMed) | **8011** |

Detailed plans: [plan-carepath-ai.md](plan-carepath-ai.md) · [plan-hedip.md](plan-hedip.md) · [plan-raip.md](plan-raip.md).

---

## Locked suite decisions

| Area | Decision |
|------|----------|
| Topology | Monorepo-style sister packages under one parent; not a single deployable |
| Coupling | **No runtime dependency** between packages. HEDIP reimplements clinical CDS; it does not call CarePath |
| Pattern reuse | LangGraph supervisor (workers never peer-route), hybrid RAG + GraphRAG, three memory layers, firewall + judges, HITL, `*_MODEL=fake` for CI, injection eval ≥ 95%, Bedrock AgentCore + Vertex Agent Engine entrypoints |
| Env isolation | `CAREPATH_*` / `HEDIP_*` / `RAIP_*` |
| Data | Synthetic only. No production PHI. No HIPAA certification claim |
| Infra | Root `docker compose up -d` starts per-project Neo4j/Postgres; RAIP also builds API + worker |
| Explicitly not v1 | Live FHIR/EHR, real CMS/PBM APIs, production RAF/HCC calculators, Kafka-in-request-path, SSO/IdP, HIPAA production hardening |

---

## Value chain (how the sisters compose)

```text
CarePath AI          HEDI Platform              RAIP Engine
care pathways   →    quality / HEDIS gaps  →   risk & incentive evidence
clinical CDS         population & claims        grounded documentation
                     performance                HCC / RAF-ready artifacts (thesis)
```

1. **CarePath** produces a defensible, HITL-gated care plan for a complex patient.
2. **HEDIP** evaluates payer/provider decisions (prior auth, claims, population risk, coding) against quality and utilization performance.
3. **RAIP** grounds documentation in approved sources so quality and risk-adjustment artifacts can be cited, versioned, and blocked when evidence is insufficient.

Interview / demo narrative: one member journey across pathway → quality gap → evidence-backed coding/documentation — still three processes, not one mesh.

---

## Shared quality bar

Each package must keep:

- Offline path with `*_MODEL=fake`
- Golden evals + injection suite **≥ 95%** before promote
- Honest `AS_BUILT.md` (implemented vs documented-only)
- HITL on sensitive publish / decision paths

---

## Workspace layout (target)

```text
healthtech-intelligence-suite/
├── .cursor/
│   ├── plan-overview.md
│   ├── plan-carepath-ai.md
│   ├── plan-hedip.md
│   └── plan-raip.md
├── carepath-ai/
├── hedip/
├── raip/
├── docker-compose.yml
├── .gitignore
└── README.md
```

If this folder is still named `carepath-&-hedip-ai-projects(heathcare-ensurance)`, rename it to `healthtech-intelligence-suite` when Cursor does not have the directory locked:

```bash
cd /c/Users/deched/projects\(ml-ai\)/mindforge-agentlab-ai-portfolio
mv "carepath-&-hedip-ai-projects(heathcare-ensurance)" healthtech-intelligence-suite
```

---

## Next execution slices

1. Keep sister READMEs and this plan set as the source of truth for naming.
2. Deepen HEDIP quality-measure (HEDIS-style) golden paths on the existing pop-health / RCM / claims domains.
3. Add RAIP risk-adjustment slices (HCC validation, RAF documentation) **on top of** the evidence store — do not replace authoring gates.
4. Optional later: shared `uv` CI composite action across the three packages.
