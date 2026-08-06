# BankShield AI — System Design

## 1. Alert → case lifecycle

```
Alert queue → Investigate (LangGraph) → Evidence pack → Risk + Recommendation
    → Grounding judge → HITL (high-risk) → SAR draft publish → Close/monitor
```

- **Queue**: synthetic alerts in `data/alerts/alerts.json`
- **Investigate**: `POST /investigate` starts a thread; workers gather evidence
- **HITL**: interrupt payload shown in UI; approve / edit / reject
- **Publish**: SAR-style package appended to `data/published_cases.log`

The system **never** auto-files a regulatory SAR without human approval on high-risk cases.

## 2. InvestigationState

See [`app/state.py`](../app/state.py). Key fields:

| Field | Role |
|-------|------|
| `alert` | Raw alert payload |
| `fraud_types` | Hypotheses from triage |
| `entities` | Customer/device/IP/phone/beneficiary |
| `identity_findings` | KYC + sanctions results |
| `txn_features` | Velocity/amount/rail/behavior |
| `evidence[]` | Append-only evidence timeline |
| `graph_paths` | Shared-entity paths |
| `reg_citations` | Hybrid RAG + live fixture docs |
| `similar_cases` | Vector-retrieved priors (worker node: `similar_case_retriever`) |
| `risk_score` / `risk_band` | Fused risk |
| `recommendation` | Explainable action pack |
| `grounding_score` | Claim–evidence quality |
| `approval` | auto / pending / approved / edited / rejected |
| `sar_draft` | Generated SAR narrative package |

## 3. Knowledge graph schema

**Nodes:** `Customer`, `Device`, `IP`, `Phone`, `Company`, `Transaction`, `Country`, `Merchant`, `Wallet` (extensible)

**Relationships:**

| Rel | Meaning |
|-----|---------|
| `OWNS` | Customer owns device/txn |
| `TRANSFERRED_TO` | Txn/customer → beneficiary |
| `SHARES_DEVICE` | Device reuse across customers |
| `SHARES_IP` | IP reuse |
| `SHARES_PHONE` | Phone reuse |
| `SHARES_BENEFICIARY` | Common payee |
| `RELATED_TO` | Soft link (country, org) |

Seeds: `data/kg/mule_ring.json`. Load via idempotent Neo4j `MERGE`, or in-memory adjacency fallback when Neo4j is down.

## 4. Corpus domains

| Domain | Content |
|--------|---------|
| `aml_policy` | BSA/SAR and mule guidance |
| `ofac_guidance` | Screening rules + fixture SDN + live feed stub |
| `fraud_playbooks` | Wire / ATO playbooks |
| `kyc_profiles` | KYC overview notes |
| `closed_cases` | Historical investigation notes |
| `sar_examples` | Narrative templates |

## 5. Deep vs shallow agents

**Deep (v1):**

- Wire/ACH: velocity, amount z-score proxy, new beneficiary, country risk
- Sanctions/AML: mock OFAC screen + regulatory RAG
- Mule: GraphRAG shared entity / fan-out detection

**Shallow (same pipeline):** card, ATO, APP/BEC, FedNow/RTP — triage labels + shared scorers/retrievers without dedicated vendor connectors.

## 6. Explainability contract

Every recommendation includes:

- `evidence_ids` (must resolve to `evidence[]`)
- `regulatory_refs` / citation docs
- `graph_explanation`
- `similar_case_ids`
- `risk_score` / `risk_band`
- `confidence`
- `reasoning` summary

Grounder rejects/revises when evidence IDs are invented or coverage is low.

## 7. Retrieval pipeline

```
Question → (optional rewrite) → Hybrid Search (BM25 + dense + RRF)
         → Lexical rerank → Context to recommender/judge
         → Live fixture feed merged for OFAC/FinCEN bulletins
```

## 8. Memory

| Layer | Store |
|-------|-------|
| Short-term | LangGraph state + Sqlite checkpointer |
| Episodic | `data/past_investigations.jsonl` (+ optional pgvector later) |
| Semantic | Chroma embeddings of corpus/cases |
| Procedural | `data/prompts/recommender_latest.json` |

## 9. Security

- Hard-block injection patterns before investigation proceeds
- Soft escalate patterns force HITL
- PII masking on SAR narrative fields
- Optional Bedrock Guardrails when configured

## 10. Deployment (stubs)

- Local: uvicorn FastAPI `:8003`
- AWS: `deploy/deploy_agentcore.sh` + `agentcore_entrypoint.py`
- GCP: `deploy/deploy_vertex_engine.sh`

Batch ingest may later use Step Functions / Cloud Workflows; **not** the investigation loop.
