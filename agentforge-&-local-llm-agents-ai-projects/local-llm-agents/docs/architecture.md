# Architecture

Educational notebook series: RAG → one agent → multi-agent on local Ollama. Precursor to [`../agentforge`](../agentforge/).

## High-Level Architecture (HLA)

```mermaid
flowchart LR
  PDF[PDF_assets]
  N1[1_rag_ipynb]
  N2[2_one_agent_ipynb]
  N3[3_multi_agent_ipynb]
  Ollama[Ollama_qwen3]
  Note[study_note_md]

  PDF --> N1
  N1 -->|TFIDF_cosine| Ollama
  N1 --> N2
  N2 -->|tools_weather_pdf_notes| Ollama
  N2 --> N3
  N3 -->|research_writer| Ollama
  N3 --> Note
```

**Notebooks:** `1_rag.ipynb` → `2_one_agent.ipynb` → `3_multi_agent.ipynb` (see [`reproduce.md`](../reproduce.md)).

## LLA omitted

These labs are linear Jupyter cells (TF-IDF retrieve → prompt → Ollama → print/file). There is no multi-service request path, so a sequence diagram would only restate notebook cell order. For a production `/chat` sequence, see [`../agentforge/docs/architecture.md`](../agentforge/docs/architecture.md).
