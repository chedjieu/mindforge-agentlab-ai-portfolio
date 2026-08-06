# Reproducing the Project

## Step 1

Install Python

Python 3.11+

---

## Step 2

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 3

Install Ollama

https://ollama.ai

---

## Step 4

Download model

```bash
ollama pull qwen3
```

---

## Step 5

Launch

```bash
ollama serve
```

---

## Step 6

Open notebooks

```bash
jupyter lab
```

---

## Notebook Order

1_rag.ipynb

↓

2_one_agent.ipynb

↓

3_multi_agent.ipynb

---

Expected Outputs

Notebook 1

- Context retrieval
- RAG responses

Notebook 2

- Tool calls
- Weather lookup
- Markdown output

Notebook 3

- Multi-agent collaboration
- Generated study notes

---

Troubleshooting

If Ollama is unavailable

```bash
ollama serve
```

Verify

```bash
ollama list
```

You should see

```
qwen3
```