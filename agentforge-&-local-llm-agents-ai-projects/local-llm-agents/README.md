# 🤖 AI Agents with Local LLMs

## Architecture

Notebook HLA (LLA omitted): [`docs/architecture.md`](docs/architecture.md)

A complete hands-on project demonstrating how to build AI Agents using only local models running with Ollama.

This project progressively introduces:

- Retrieval-Augmented Generation (RAG)
- Tool Calling
- Single AI Agent
- Multi-Agent Collaboration
- Local LLMs
- PDF Question Answering
- Weather API Integration
- Automatic Study Note Generation

Everything runs locally.

---

# Project Structure

```
local-llm-agents
│
├── 1_rag.ipynb
├── 2_one_agent.ipynb
├── 3_multi_agent.ipynb
│
├── assets/
│   └── claude_certification_foundation_associate.pdf
│
├── study_note.md
├── requirements.txt
├── reproduce.md
└── README.md
```

---

# Notebook 1

Simple Retrieval Augmented Generation

Topics

- Read PDF
- Chunk PDF
- TF-IDF
- Cosine Similarity
- Prompt Engineering
- Local LLM

---

# Notebook 2

Single AI Agent

Capabilities

- Search PDF
- Get Weather
- Write Markdown
- Tool Calling
- Function Schemas

---

# Notebook 3

Multi Agent Workflow

Agents

Research Agent

↓

Writer Agent

↓

Study Note

---

# Requirements

Python 3.11+

Ollama

Qwen 3

PyPDF

Scikit-Learn

Requests

---

# Install

```bash
pip install -r requirements.txt
```

Install Ollama

```bash
ollama pull qwen3
```

Run

```bash
jupyter lab
```

---

# Architecture

```
User Question
      │
      ▼
   Retriever
      │
      ▼
 Context Builder
      │
      ▼
     Ollama
      │
      ▼
     Answer
```

Notebook 2

```
User
 │
 ▼
Agent
 │
 ├── Search PDF
 ├── Weather
 └── Write Markdown
```

Notebook 3

```
User
 │
 ▼
Research Agent
 │
 ▼
Writer Agent
 │
 ▼
study_note.md
```

---

# Technologies

- Python
- Ollama
- Qwen
- PyPDF
- Requests
- Markdown
- Jupyter
- TF-IDF
- Cosine Similarity
- JSON Schema