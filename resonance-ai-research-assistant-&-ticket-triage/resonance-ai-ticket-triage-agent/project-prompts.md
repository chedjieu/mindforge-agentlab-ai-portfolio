# Panasonic EGKP — Cursor prompt library

Every Cursor Composer prompt for the **Enterprise Generative AI Knowledge Platform** (`panasonic-egkp`), reverse-engineered from Monk Project 2 (`project2-prompts.md` / `monk-ticket-triage`) and upgraded for production RAG, GraphRAG, HITL, dual-cloud deploy, and LLM-as-judge gates.

> **How to use**: Paste each blockquote into Cursor Composer in order. Prompt IDs like `Day 2 H1` are stable references. Locked decisions live in [`AS_BUILT.md`](AS_BUILT.md); architecture narrative in [`docs/architecture.md`](docs/architecture.md).
>
> **Session mapping (suggested)**: Day 1 = skeleton + ingest. Day 2 = retrieval, graph, synthesizer, HITL. Day 3 = dual-cloud deploy. Day 4 = judges + security. Bonus = ops stretch.

---

## Day 1 H1 — Project skeleton (supervisor + stubs)

> Initialize the project at the repo root (package name `panasonic-egkp`). Create the following structure with stub implementations. Follow locked decisions in `AS_BUILT.md`.
>
> 1. `app/state.py` defining `class KnowledgeState(TypedDict)` with fields:
>    - `thread_id: str`
>    - `user_id: str`
>    - `role: str`
>    - `domain: Literal["engineering", "manufacturing", "hr", "support", "operations"] | None`
>    - `query: str`
>    - `intent: Literal["factoid", "procedure", "policy", "troubleshooting", "relationship", "unknown"] | None`
>    - `needs_graph: bool`
>    - `sensitivity: Literal["normal", "sensitive"]`
>    - `retrieved_chunks: list[dict]`
>    - `graph_paths: list[dict]`
>    - `draft_answer: dict | None`
>    - `citations: list[dict]`
>    - `grounding_score: float | None`
>    - `revise_count: int`
>    - `approval: Literal["pending", "approved", "edited", "rejected", "auto"]`
>    - `published: bool`
>    - `step_log: list[str]`
>    - `next: str | None`
>
> 2. `app/agents/supervisor.py` with `supervisor_node(state) -> dict`. Returns `{"next": ...}` based on rules (pure logic, no LLM):
>    - If `approval == "rejected"`: `"END"`.
>    - Else if `intent is None`: `"intent_router"`.
>    - Else if `retrieved_chunks == []`: `"retriever"`.
>    - Else if `needs_graph and graph_paths == []`: `"graph_walker"`.
>    - Else if `draft_answer is None`: `"synthesizer"`.
>    - Else if `grounding_score is None`: `"grounder"`.
>    - Else if `approval == "pending"`: `"hitl"`.
>    - Else if `approval in ("approved", "edited", "auto")` and not `published`: `"answer_publish"`.
>    - Else `"END"`.
>
> 3. Stub workers as functions that append a `step_log` line and return minimal placeholders:
>    - `app/agents/intent_router.py`
>    - `app/agents/retriever.py`
>    - `app/agents/graph_walker.py`
>    - `app/agents/synthesizer.py`
>    - `app/agents/grounder.py`
>    - `app/agents/hitl.py`
>    - `app/agents/answer_publish.py`
>
> 4. `app/graph.py` that wires `START -> supervisor` and from supervisor uses `add_conditional_edges` to route to the named node. Each worker returns to supervisor. Use a `SqliteSaver` for now. Export `build_graph()` and later-ready `build_graph_with_backends(saver, store)`.
>
> 5. `app/llm.py` reading `EGKP_MODEL` (default Bedrock `gpt-oss-120b` converse id from AS_BUILT) with `fake` support via `app/_fake_llm.py`.
>
> 6. `app/guardrails.py` with hard-block injection pattern check; on block set `approval="rejected"` and skip workers.
>
> 7. `pyproject.toml` for Python 3.11+, `langgraph`, `langchain`, `fastapi`, `pydantic`, `chromadb`, `neo4j`, `uv` tooling.
>
> Add a small `__main__` test in `app/graph.py` that feeds a sample manufacturing query and prints each routing step.

---

## Day 1 H2 — Ingestion pipeline + synthetic corpus + vectors

> Build the knowledge ingest path and NDA-safe corpus. Spec details are in `docs/architecture.md` (corpus / knowledge section).
>
> 1. Create `scripts/generate_synthetic_corpus.py` that writes:
>    - At least 6 markdown docs per domain under `data/corpus/{manufacturing,engineering,support,hr,operations}/` with YAML frontmatter (`doc_id`, `domain`, `doc_type`, `plant`, `acl_roles`, `effective_date`, `supersedes`, `entities`).
>    - `data/kg/seed_entities.jsonl` (≥ 40 entities) and `data/kg/seed_relations.jsonl` (≥ 60 relations) using labels/rels from `docs/architecture.md`.
>    - Include explicit supersession (e.g. `SOP-M-105` SUPERSEDES `SOP-M-104`) and HR policy ↔ role edges for HITL demos.
>
> 2. Create `app/ingest/pipeline.py` with:
>    - `load_documents(corpus_root) -> list[Document]`
>    - `chunk_documents(docs) -> list[Chunk]` heading-aware; preserve metadata + `acl_roles`
>    - `embed_and_upsert(chunks, backend)` where backend is selected by `EGKP_VECTORS` (`chroma` default → `data/chroma/`; `pgvector` optional)
>    - `load_kg_seeds(neo4j_driver)` loading entities/relations into Neo4j (idempotent MERGE)
>    - CLI: `python -m app.ingest.pipeline` runs full local ingest
>
> 3. Create `deploy/ingest_step_functions.json` and `deploy/ingest_cloud_workflows.yaml` as **stubs** describing bronze→silver→gold→index steps (no need to deploy yet). Chat loop must NOT call Step Functions.
>
> 4. Add a smoke test: after generate + ingest, hybrid search for `PN-4421 torque` returns ≥ 1 chunk from manufacturing.

---

## Day 2 H1 — Hybrid retriever worker

> Replace the stub in `app/agents/retriever.py` and add tools under `app/tools/`.
>
> 1. `app/tools/hybrid_search.py`:
>    - `hybrid_search(query: str, domain: str | None, role: str, k: int = 8) -> list[dict]`
>    - Combine dense (Chroma) + BM25 over the same corpus; fuse with reciprocal rank fusion.
>    - Filter chunks where `role` intersects `metadata.acl_roles` (if `acl_roles` empty, allow).
>    - Each result: `{"chunk_id", "doc_id", "text", "score", "metadata"}`.
>
> 2. `app/tools/rerank.py`:
>    - `rerank_chunks(query: str, chunks: list[dict], n: int = 5) -> list[dict]`
>    - Simple LLM or cross-encoder rerank; with `EGKP_MODEL=fake`, use score = token overlap.
>
> 3. `retriever_node(state)`:
>    - Call hybrid_search then rerank.
>    - Return `{"retrieved_chunks": [...], "step_log": [...]}`.
>    - Log truncated query and top chunk_ids.
>
> 4. If zero chunks survive ACL filters, still return `retrieved_chunks` as a single placeholder dict `{"chunk_id": "EMPTY", "text": "", "score": 0.0, "metadata": {"empty": true}}` so the supervisor does not infinite-loop; synthesizer must refuse with “no authorized sources”.

---

## Day 2 H2 — Neo4j GraphWalker

> Replace the stub in `app/agents/graph_walker.py`.
>
> 1. `app/tools/neo4j_graph.py`:
>    - `lookup_entity(name_or_id: str) -> dict | None`
>    - `traverse_relations(entity_id: str, rel_types: list[str] | None = None, hops: int = 2) -> list[dict]`
>    - Wrap with `@tool`. Use env `EGKP_NEO4J_URI`, `EGKP_NEO4J_USER`, `EGKP_NEO4J_PASSWORD`.
>    - If Neo4j is down, fall back to scanning `data/kg/seed_*.jsonl` in-process.
>
> 2. `graph_walker_node(state)`:
>    - Only meaningful when `state["needs_graph"]` is true (still safe if called).
>    - Bind tools to the chat model; budget **max 6** tool calls.
>    - System prompt: extract entities from the query + top chunk entity lists; traverse SUPERSEDES / APPLIES_TO / GOVERNS / REQUIRES / LOCATED_AT as needed; stop when you can answer the relationship question.
>    - After the loop, summarize `graph_paths` as `[{"nodes": [...], "rels": [...], "rationale": str}]`.
>    - Return `{"graph_paths": [...], "step_log": [...]}`.
>
> 3. Update `intent_router` (next prompt may flesh fully) so relationship questions set `needs_graph=True`. For now, if query contains “supersed”, “which SOP”, “applies to”, or “related to”, set `needs_graph=True` in a temporary heuristic inside graph_walker’s caller path — prefer implementing cleanly in Day 2 H3 intent_router.

---

## Day 2 H3 — Intent router, synthesizer, three memory layers

**Intent router first:**

> Replace `app/agents/intent_router.py`:
>
> 1. Pydantic `IntentOutput` with `domain`, `intent`, `sensitivity`, `needs_graph`, `confidence`, `rationale`.
> 2. Use `init_chat_model(...).with_structured_output(IntentOutput)`.
> 3. Prompt: classify into the five domains and six intents; mark `hr` or PII-like requests `sensitivity="sensitive"`; mark supersession/applicability questions `needs_graph=true`.
> 4. Return fields onto state; append step_log.
> 5. Validate domain membership; on failure default `domain="support"`, `intent="unknown"`, `sensitivity="normal"`.

**Memory:**

> Create three files in `app/memory/`:
>
> 1. `semantic.py` — `recall_user(user_id, k)` and `remember_user(user_id, content)` over LangGraph Store (`EGKP_MEMORY=memory|postgres`).
> 2. `episodic.py` — `similar_past_qa(query, domain, k=3) -> list[dict]` backed by pgvector table `past_qa_resolutions` or `data/{domain}/historical_qa.jsonl` fallback.
> 3. `procedural.py` — `get_answerer_prompt(domain, version="latest")` / `set_answerer_prompt(...)` reading `data/prompts/answerer_{domain}.json` with version history. Ship default prompts that require citations and forbid inventing policy/SLA/numbers.

**Synthesizer:**

> Replace `app/agents/synthesizer.py`:
>
> 1. Load procedural prompt via `get_answerer_prompt(state["domain"])`.
> 2. Pull 3 episodic examples via `similar_past_qa`.
> 3. Pull semantic memories via `recall_user(state["user_id"], k=3)`.
> 4. Build messages: system = procedural; few-shot episodic; “Known about user/role”; then query + chunks + graph_paths.
> 5. `SynthesizerOutput`: `{answer: str, citations: list[{"citation_id", "chunk_id", "doc_id", "quote"}], confidence: float, risk_flags: list[str], recommended_action: Literal["publish", "hitl"]}`.
> 6. Post-process: if `confidence < 0.6`, or domain `hr`, or risk flags include `pii`/`legal`, or empty evidence, force `recommended_action="hitl"`.
> 7. Set `approval` to `"pending"` when HITL required else `"auto"`.
> 8. Return `draft_answer`, `citations`, `approval`, `step_log`.

---

## Day 2 H4 — Grounder + HITL + FastAPI approval console

> Create `app/agents/grounder.py` (replace stub):
>
> 1. Split `draft_answer["answer"]` into claims (sentence-level is fine).
> 2. For each claim, check support against cited chunk texts (LLM structured or fake overlap).
> 3. Compute `grounding_score` in `[0,1]` = supported_claims / max(total_claims, 1).
> 4. If `grounding_score < 0.7` and `revise_count < 2`: return `{"draft_answer": None, "grounding_score": None, "revise_count": revise_count+1, ...}` to force synthesizer revise (supervisor routes on empty draft).
> 5. If still low after revisions: force `approval="pending"` and add risk flag `low_grounding`.
> 6. Otherwise set `grounding_score` and leave approval as-is.
>
> Create `app/hitl.py` used by `app/agents/hitl.py`:
>
> 1. `hitl_node(state)` calls `interrupt({draft, citations, grounding_score, domain, query, retrieved_chunks, graph_paths})`.
> 2. Resume payload: `{"action": "approve"|"edit"|"reject", "edited_body": str | None}`.
> 3. Map to `approval` and optionally overwrite `draft_answer["answer"]`.
>
> Create `app/agents/answer_publish.py`:
>
> 1. Only runs if `approval in ("approved", "edited", "auto")`.
> 2. Append JSON line to `data/published_answers.log` via `app/tools/publish_answer.py`.
> 3. If `grounding_score` is not None and `< float(os.getenv("GROUNDING_SHIP_THRESHOLD", "0.85"))`, also call `notify_slack("#egkp-quality", blocks)` mock.
> 4. Return `{"published": True, "step_log": [...]}`.
>
> Update `app/main.py` (FastAPI):
>
> 1. `POST /ask` with `{query, user_id, role, domain?}` — create `thread_id`, run graph in background.
> 2. `POST /ask/demo` — manufacturing PN-4421 torque demo query.
> 3. `GET /pending` — paused HITL payloads.
> 4. `POST /approve/{thread_id}` with action payload; resume via `Command(resume=...)`.
> 5. Serve `app/ui/approval.html` on `/` — fetch-poll every 5s; show query, domain, citations, grounding score, editable answer, Approve / Save&Approve / Reject.
> 6. Bind host/port from `HOST`/`PORT` default `127.0.0.1:8002`.

---

## Day 3 H1 — Bedrock AgentCore deploy

> Create `deploy/agentcore_entrypoint.py`:
>
> ```python
> import os
> from bedrock_agentcore import BedrockAgentCoreApp
> from langgraph.checkpoint.postgres import PostgresSaver
> from langgraph.store.postgres import PostgresStore
> from app.graph import build_graph_with_backends
>
> app = BedrockAgentCoreApp()
>
> @app.entrypoint
> async def handler(payload, context):
>     graph = build_graph_with_backends(
>         saver=PostgresSaver.from_conn_string(os.environ["POSTGRES_DSN"]),
>         store=PostgresStore.from_conn_string(os.environ["POSTGRES_DSN"]),
>     )
>     config = {"configurable": {"thread_id": context.session_id}}
>     async for event in graph.astream_events(payload, config=config, version="v2"):
>         await app.streaming.write(event)
> ```
>
> Also create `deploy/deploy_agentcore.sh`:
>
> ```bash
> #!/usr/bin/env bash
> set -euo pipefail
> agentcore configure \
>     --name panasonic-egkp \
>     --entrypoint deploy/agentcore_entrypoint.py \
>     --runtime python3.11 \
>     --memory 1024 \
>     --timeout 600
> agentcore launch
> echo "Done. agentcore logs panasonic-egkp --follow"
> ```
>
> Ensure `app/graph.py` exports `build_graph_with_backends(saver, store)` in addition to local `build_graph()`. Set `DISABLE_AGENTCORE_MEMORY=1` by default in docs.

---

## Day 3 H2 — Vertex AI Agent Engine deploy

> Create `deploy/vertex_engine_deploy.py`:
>
> ```python
> import os
> import vertexai
> from vertexai import agent_engines
> from app.graph import build_graph
>
> vertexai.init(
>     project=os.environ["GCP_PROJECT"],
>     location=os.environ.get("GCP_LOCATION", "us-central1"),
>     staging_bucket=f"gs://{os.environ['GCP_BUCKET']}",
> )
>
> langgraph_agent = agent_engines.LanggraphAgent(
>     model="gemini-2.5-pro",
>     runnable=build_graph(),
>     enable_tracing=True,
> )
>
> deployed = agent_engines.create(
>     langgraph_agent,
>     requirements=[
>         "langgraph>=1.2,<2",
>         "langchain-google-vertexai",
>         "psycopg[binary]",
>         "pydantic>=2",
>         "chromadb",
>         "neo4j",
>         "pyyaml",
>     ],
>     display_name="panasonic-egkp",
> )
> print("Deployed:", deployed.resource_name)
> ```
>
> Also create `deploy/deploy_vertex_engine.sh` that runs the above and saves the resource name to `.env.deployed`.

---

## Day 4 H1 — LLM-as-judge suite + bias mitigations + deploy gates

> Create judge infrastructure that **gates decisions** (ship retrieval, gate deploy, report quality). Read failure-mode rules in `AS_BUILT.md`.
>
> 1. `app/eval/judge_client.py`:
>    - `get_judge_model()` reads `EGKP_JUDGE_MODEL`.
>    - Assert at runtime (when not `fake`) that judge provider ≠ answerer provider; if misconfigured, raise `RuntimeError("same-model bias: configure EGKP_JUDGE_MODEL on the other cloud")`.
>    - Provide `judge_chat(messages) -> str` with timeout; on failure return `None` (caller fail-closed for gates).
>
> 2. Rubrics under `evals/rubrics/`:
>    - `groundedness.md` — claim–evidence entailment; unsupported claim ⇒ fail
>    - `answer_quality.md` — scores 1–5 for accuracy, completeness, citation, safety; **penalize verbosity** that adds no grounded claims; instruct judge to ignore length as a quality signal
>    - `retrieval.md` — relevance + coverage + ACL correctness
>    - `pairwise.md` — choose A or B; ignore position; justify briefly
>
> 3. `evals/retrieval_judge.py` — golden `evals/retrieval_golden.jsonl`; score relevance/coverage; print pass-rate; upload LangSmith experiment `egkp-retrieval-judge`.
>
> 4. `evals/groundedness_judge.py` — golden `evals/groundedness_golden.jsonl`; pass if score ≥ `GROUNDING_SHIP_THRESHOLD` (default 0.85); **fail closed** if judge returns None; LangSmith `egkp-groundedness-judge`.
>
> 5. `evals/answer_quality_judge.py` — rubric 1–5; also compute `length_normalized_score = quality / log2(2 + token_count)` for reporting (verbosity bias mitigation); LangSmith `egkp-answer-quality`.
>
> 6. `evals/pairwise_regression.py`:
>    - Inputs: baseline answers vs candidate answers on the same golden queries (or regenerate with `EGKP_CANDIDATE_PROMPT_VERSION`).
>    - Randomize A/B order per row; map judge winner back to baseline/candidate.
>    - Deploy gate: candidate win-rate ≥ baseline (configurable `PAIRWISE_MIN_WIN_RATE`, default 0.50 with tie handling).
>    - Fail closed on judge errors.
>    - LangSmith `egkp-pairwise-regression`.
>
> 7. `evals/e2e_eval.py` — full graph on `evals/golden.jsonl` (≥ 25 rows). Pass = correct domain + citation present + grounding ≥ threshold + correct HITL expectation.
>
> 8. `evals/run_all.py` — runs all judges + e2e; exits non-zero if any ship gate fails.
>
> 9. Document in `evals/README.md` which scripts gate **ship retrieval**, **gate deploy**, and **report only**.

---

## Day 4 H2 — Security injection eval

> Create `security/attacks.jsonl` with 20 attack payloads as query strings, each labelled `name` and `expected_outcome` (`blocked` or `escalated`).
>
> Include variants of: ignore previous instructions, DAN jailbreak, exfiltrate HR salaries, reveal system prompt, skip HITL / auto-publish, markdown link smuggling, encoded instructions, tool-call exfil, privilege escalation via role spoof in query body.
>
> Create `security/injection_eval.py`:
>
> 1. For each attack, feed through the full pipeline (auto-resume HITL as reject if needed for outcome detection).
> 2. `blocked` = guardrail refusal OR `approval == "rejected"` before publish.
> 3. `escalated` = HITL pending or synthesizer/grounder forced `recommended_action="hitl"` / low grounding path.
> 4. Print per-attack pass/fail; require pass-rate ≥ 95% (19/20).
> 5. Support `EGKP_MODEL=fake` with deterministic outcomes for CI.

---

## Day 4 H3 — Billing alerts (optional ops)

> Create `scripts/setup_billing_alerts.sh`:
>
> ```bash
> #!/usr/bin/env bash
> set -euo pipefail
> EMAIL="${ALERT_EMAIL:?set ALERT_EMAIL}"
>
> aws budgets create-budget --account-id "$(aws sts get-caller-identity --query Account --output text)" \
>     --budget '{"BudgetName":"panasonic-egkp-daily","BudgetLimit":{"Amount":"10","Unit":"USD"},"TimeUnit":"DAILY","BudgetType":"COST"}' \
>     --notifications-with-subscribers '[{"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":100},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"'"$EMAIL"'"}]}]'
>
> BILLING_ACCOUNT="$(gcloud billing accounts list --format='value(name)' --limit=1)"
> gcloud billing budgets create \
>     --billing-account="$BILLING_ACCOUNT" \
>     --display-name="panasonic-egkp-daily" \
>     --budget-amount="10USD" \
>     --threshold-rule=percent=1.0,basis=current-spend \
>     --calendar-period=daily
> echo "Alerts set up. Watch $EMAIL."
> ```

---

## Bonus stretch prompts

**Auto-prompt-tuning:**

> Add `app/cron/refine_answerer_prompt.py`: pull the last 50 HITL outcomes from `data/hitl_outcomes.jsonl`, ask the LLM to summarise common human edits, and propose a `v+1` procedural prompt for a given `--domain`. Print to stdout only; do **not** write `data/prompts/` automatically.

**Slack quality notifier:**

> Add `app/tools/notify_slack.py` exporting `notify_slack(channel: str, blocks: list[dict])`. Wire into `answer_publish` when grounding is below threshold; mock to `data/slack_notifications.log` when `SLACK_BOT_TOKEN` is unset.

**Bedrock KB swap for retrieval:**

> When `EGKP_VECTORS=bedrock_kb` and `BEDROCK_KB_ID` is set, replace the body of `hybrid_search` to query Bedrock Knowledge Bases. Keep the function signature identical. Keep Chroma path for local demos.

**Ops dashboard:**

> Create `app/ops/dashboard.py` — Streamlit app showing: today’s queries by domain (bar), grounding score histogram, HITL rate, P50 latency proxy from step_log timestamps if present, last 20 published answers with status badges.

**Vertex Vector Search swap:**

> When `EGKP_VECTORS=vertex`, implement a thin adapter that queries Vertex AI Vector Search with the same return schema as Chroma results. Document required env vars in `AS_BUILT.md` (do not break local chroma default).

---

## Prompt engineering notes (for instructors / self)

When improvising follow-ups in Composer, keep these constraints explicit:

1. Workers never call each other — only supervisor routes.  
2. Judge model must be cross-provider vs answerer.  
3. HR domain always HITL.  
4. Citations required; no invented numbers/SLAs.  
5. Graph walker budget ≤ 6; prefer MERGE idempotent KG loads.  
6. Prefer editing `AS_BUILT.md` checklist when behavior is intentionally changed.

---

## Mapping from Monk Project 2 → EGKP

| Project 2 concept | EGKP analogue |
|-------------------|---------------|
| Ticket triage domains | Knowledge domains (eng/mfg/hr/support/ops) |
| Triager | Intent router |
| Investigator + tools | Retriever + Graph walker |
| Responder | Synthesizer |
| (implicit quality) | Grounder + LLM-as-judge gates |
| HITL approve send | HITL approve publish |
| Send node | Answer publish |
| `MONK_*` env | `EGKP_*` env |
| Runbooks corpus | Multi-domain corpus + Neo4j seeds |
| Injection ≥ 95% | Same bar + groundedness ≥ 0.85 ship |

---

*Paste prompts verbatim for consistency across models. After each day, run the verification checklist in [`AS_BUILT.md`](AS_BUILT.md).*
