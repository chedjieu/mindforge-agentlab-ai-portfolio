# As-Built — Local LLM Agents

**Document type:** Planning documentation — *as built*  
**Status:** Implemented educational notebook series  
**Package:** `local-llm-agents`  
**Location:** `8.agentforge-&-local-llm-agents-ai-projects/local-llm-agents/`  
**Related:** [README.md](README.md) · [reproduce.md](reproduce.md) · production evolution in [`../agentforge/`](../agentforge/)

This file captures the hands-on learning project **as delivered**: progression, locked choices, architecture per notebook, layout, and verification.

---

## 1. Project objective

Demonstrate how to build AI agents using **only local models** (Ollama), progressing from simple RAG to tool-calling and multi-agent collaboration — without cloud LLM APIs.

By the end, the operator can:

1. Build PDF Q&A with TF-IDF retrieval + a local LLM  
2. Run a single agent with tool calling (PDF search, weather, markdown write)  
3. Orchestrate Research → Writer multi-agent collaboration into `study_note.md`

---

## 2. Locked decisions (as built)

| Area | Decision |
|------|----------|
| Runtime | Fully local — **Ollama** required |
| LLM | **Qwen 3** (`ollama pull qwen3`) |
| Embeddings / retrieval (NB1) | **TF-IDF** + cosine similarity (scikit-learn) — not dense vectors |
| Document source | PDF under `assets/` (Claude certification foundation associate materials) |
| Agent framework | Notebook-native Python (no LangGraph / FastAPI in this package) |
| Tools (NB2) | Search PDF · Get weather · Write markdown |
| Multi-agent (NB3) | Research Agent → Writer Agent → study note file |
| UI | Jupyter Lab / Notebook |
| Python | 3.11+ |
| Explicitly not this package | Chroma, LangGraph, FastAPI, Streamlit, guardrails, Docker — see AgentForge |

### Do not regress

1. Keep the three-notebook progressive path (`1` → `2` → `3`).  
2. Remain runnable offline aside from the weather HTTP call.  
3. Answers in NB1 should stay grounded to retrieved PDF context.  
4. AgentForge may replace TF-IDF/Chroma patterns — this package stays the pedagogical baseline.

---

## 3. Notebook progression (as built)

### Notebook 1 — `1_rag.ipynb`

**Simple RAG**

```text
PDF → Extract → Chunk → TF-IDF Index
                              ↓
                     User Question → Similarity Search
                              ↓
                     Context Builder → Ollama → Answer
```

Topics: PDF read, chunking, TF-IDF, cosine similarity, prompt engineering, local LLM, context-restricted answers.

### Notebook 2 — `2_one_agent.ipynb`

**Single agent + tools**

```text
User → Agent
         ├── Search PDF
         ├── Weather (external API)
         └── Write Markdown
```

Topics: tool calling, function schemas, PDF search, weather lookup, markdown output.

### Notebook 3 — `3_multi_agent.ipynb`

**Multi-agent workflow**

```text
User → Research Agent → Writer Agent → study_note.md
```

Topics: agent collaboration, research notes → polished study guide.

---

## 4. Project layout (as built)

```text
local-llm-agents/
├── AS_BUILT.md
├── README.md
├── reproduce.md
├── requirements.txt
├── .gitignore
├── 1_rag.ipynb
├── 2_one_agent.ipynb
├── 3_multi_agent.ipynb
└── assets/
    └── claude_certification_foundation_associate.pdf   # (or equivalent PDF)
```

Runtime artifacts (e.g. generated study notes) may appear beside notebooks when cells are executed.

---

## 5. Dependencies (as built)

From `requirements.txt`:

| Package | Role |
|---------|------|
| `ollama` | Local LLM client |
| `pypdf` | PDF text extraction |
| `scikit-learn` / `numpy` / `pandas` | TF-IDF + similarity |
| `requests` | Weather / HTTP tools |
| `jupyterlab` / `notebook` / `ipykernel` | Notebook runtime |
| `matplotlib` / `tqdm` | Viz / progress |

---

## 6. Reproduce (as built)

See [reproduce.md](reproduce.md). Short path:

```bash
pip install -r requirements.txt
ollama pull qwen3
ollama serve
jupyter lab
```

Run notebooks in order: `1_rag.ipynb` → `2_one_agent.ipynb` → `3_multi_agent.ipynb`.

---

## 7. Expected outputs & verification

| Notebook | Expected |
|----------|----------|
| 1 | Context retrieval + grounded RAG answers from the PDF |
| 2 | Tool calls (PDF / weather / markdown write) |
| 3 | Multi-agent collaboration producing study notes |

### Checklist

- [x] Three progressive notebooks committed  
- [x] `requirements.txt` + `reproduce.md` runbook  
- [x] README with architecture diagrams per notebook  
- [x] Assets path for certification PDF  
- [x] Production evolution documented in sibling AgentForge  

---

## 8. Relationship to AgentForge

| Concern | `local-llm-agents` | `agentforge` |
|---------|--------------------|--------------|
| Form | Jupyter notebooks | Deployable app |
| Retrieval | TF-IDF | Ollama embeddings + Chroma |
| Orchestration | Notebook cells | LangGraph supervisor |
| Surface | Cell output | FastAPI + Streamlit |
| Safety / eval / deploy | None | Guardrails, `/eval`, Docker/k8s |
