# Architecture talking points (RAIP)

Diagrams: [high-level](../architecture/HIGH_LEVEL.md) · [low-level](../architecture/LOW_LEVEL.md). As-built: [`../../AS_BUILT.md`](../../AS_BUILT.md).

**Why agents?** Not for theatre. Each node has a distinct contract: retrieve, draft, verify, gate. The supervisor never writes clinical text. Peer-routing is forbidden (CarePath lesson).

**Why LangGraph?** Explicit state machine, HITL `interrupt`, checkpointer, loop cap. Better than an ad-hoc chain for audit.

**Why GraphRAG?** Vector search cannot express “v2 supersedes v1” or claim–evidence edges. Neo4j is optional; Postgres stores the FK so the graph is not a single point of failure.

**Why claim-level grounding?** Citations can be hallucinated. Support status on each material claim is the control that blocks publish.

**Why HITL?** High-risk clinical/regulatory text. The model cannot be the last gate.

**How do you prevent hallucination?** Eight layers: grounding prompt, evidence-only context, claim extract, match, contradiction, citation check, safety gate, human. No single LLM call is treated as safety.

**Conflicting guidelines?** Detect; prefer higher authority and supersession; if still material, HITL. Never silent merge.

**Outdated sources?** `effective_date` + `supersedes_version_id`. Superseded chunks dropped from default retrieval.

**Evaluate grounding?** Deterministic unsupported-claim rate, citation completeness, plus optional cross-provider judge.

**Prompt injection?** PDFs are data. Delimiters, scanners, output gates, 50-attack suite ≥95%.

**Scale ingest?** Upload → object store → job row → worker. Swap SQL queue for SQS without changing parsers.

**Model failure?** Gateway falls back to fake in local/throttle; production should fail closed on evidence path (no draft without retrieval).

**Cost?** Token estimates on state; route simple tasks to cheaper models later. Verification should stay on a separate judge when possible.

**Prove provenance?** `request_id` reconstructs sources, chunks, model, prompt, claims, review.

**AWS?** Bedrock + AgentCore entrypoint, RDS pgvector, S3, OpenSearch optional.

**GCP?** Vertex + Agent Engine entrypoint, Cloud SQL, GCS.

**Pilot to scale?** One template, synthetic data, HITL always on, eval gates in CI, then tenants and document types.

**If cost is a constraint?** Drop Neo4j first (keep SQL supersession), heuristic rerank, fewer LLM nodes (keep claim verify deterministic), SQLite not viable in prod — keep Postgres.

**Real regulated deployment?** IdP, BAA, OCR, DLP, ClamAV, change control on prompts, human validation study, no autonomous diagnosis claims.
