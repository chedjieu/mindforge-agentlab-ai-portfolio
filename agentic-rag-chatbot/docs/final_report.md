# Final Report — Agentic RAG Chatbot

## 1. Overview

This prototype is an **AI Research Knowledge Assistant** over Lilian Weng’s blog posts. It combines:

- **RAG** — retrieve relevant passages from a Chroma vector store, then generate grounded answers with GPT-4o.
- **Agentic behavior** — a LangChain tool-calling loop that chooses KB search, source lookup, and/or web search.
- **n8n orchestration** — Chat UI, query logging, and optional Slack/webhook escalation.

## 2. How RAG works in this project

```text
Question
   → embed query (text-embedding-3-small)
   → similarity search in Chroma (top-k chunks)
   → agent reads chunks as tool output
   → GPT-4o writes answer + citations
```

**Why RAG helps:** The model is not forced to rely only on parametric memory. Answers can point back to the posts that were indexed (title + URL), which reduces unsupported claims on corpus topics and makes the demo auditable.

### Screenshot: ingestion

> **[Screenshot placeholder]** Terminal output of `python -m src.ingest` showing documents loaded and chunk counts.

### Screenshot: API health / chat

> **[Screenshot placeholder]** Browser or curl showing `GET /health` with a non-zero `knowledge_base_documents`, and a sample `POST /chat` JSON response with `answer`, `sources`, and `steps`.

## 3. How agentic behavior works

Unlike a single-shot “retrieve then answer” chain, the agent:

1. Receives a system prompt that prefers KB tools first.
2. May call tools multiple times (search → refine → cite).
3. Returns `steps` so the demo can show *which tools ran*.

| Tool | Role |
|------|------|
| `search_knowledge_base_tool` | Semantic search over Lilian Weng posts |
| `get_source_summary` | Metadata + snippet for a title/URL |
| `web_search` | Fallback for out-of-KB questions |

### Screenshot: tool steps

> **[Screenshot placeholder]** Chat response (API or n8n) where `steps` lists `search_knowledge_base_tool` (and optionally `web_search` for an out-of-domain question).

### Screenshot: n8n Chat UI

> **[Screenshot placeholder]** n8n Chat Trigger conversation answering e.g. “What causes extrinsic hallucinations in LLMs?” with a Sources section.

### Screenshot: logging / escalation

> **[Screenshot placeholder]** File under `data/logs/` and/or n8n execution log; optional webhook/Slack message after a query containing `escalate`.

## 4. Challenges faced

### 4.1 Hallucinations

Even with RAG, models can over-generalize or blend posts. Mitigation: system prompt requires KB-first retrieval, citations, and explicit uncertainty when evidence is weak.

### 4.2 Retrieval quality

Chunk boundaries can split definitions across pieces; similarity search may return related but not exact sections. Tuning `CHUNK_SIZE`, `CHUNK_OVERLAP`, and `TOP_K` helps. Re-ingesting after improving HTML extraction also improves recall.

### 4.3 Web page extraction

Blog HTML includes nav/footer noise. The ingest pipeline targets `article` / `main` and strips scripts/styles; still, site layout changes can break extraction for individual URLs (logged as failed fetches).

### 4.4 Latency and cost

Each chat turn may include multiple LLM + embedding/tool calls. Acceptable for a prototype; production would cache embeddings, stream tokens, and add evaluation gates.

### 4.5 n8n ↔ local API networking

Dockerized n8n cannot use `localhost` for the host API. The workflow uses `host.docker.internal:8000` (documented in the README).

## 5. Evaluation notes (manual demo)

| Query | Expected behavior |
|-------|-------------------|
| What causes extrinsic hallucinations in LLMs? | KB retrieval + answer citing the hallucination post |
| Summarize LLM-powered autonomous agents | KB retrieval + structured summary with source URL |
| How do diffusion models generate video? | KB retrieval from diffusion-video / diffusion posts |
| What’s the weather in Toronto? | Web search or honest refusal — not a fake KB citation |

## 6. Future improvements

1. **Hybrid search** — combine dense vectors with BM25 for acronyms and exact terms.
2. **RAG evaluation** — add a small golden Q&A set; track faithfulness / citation precision.
3. **Reranking** — cross-encoder rerank of top-k chunks before generation.
4. **Conversation memory** — per-session history with summarization.
5. **Auth & rate limits** — protect the public n8n chat and API key usage.
6. **Streaming** — token streaming through FastAPI + n8n for snappier UX.
7. **Richer notifications** — email + Slack with answer snippets and source links.
8. **UI polish** — dedicated Gradio/Streamlit frontend alongside n8n for grading demos.

## 7. Conclusion

The prototype demonstrates the full course deliverable stack: curated KB ingestion, semantic retrieval, grounded generation, agent tool use, and n8n orchestration with logging and external hooks. Together, RAG and agentic tooling make the assistant more transparent and more useful than a plain chatbot over the same corpus.
