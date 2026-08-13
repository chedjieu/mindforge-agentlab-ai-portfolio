# CarePath AI — Implementation Plan

Day-ordered build order aligned with `project-prompts.md`.

1. Lock AS_BUILT + SYSTEM_DESIGN + ARCHITECTURE (done).
2. Scaffold package, state, firewall, fake LLM, FastAPI console (:8007).
3. Hybrid RAG + Neo4j/JSONL GraphRAG + patient/corpus seeds.
4. Memory layers (procedural / episodic / semantic).
5. Supervisor + five workers + revise loop.
6. Evaluator judge + HITL + plan publish audit.
7. Clinician console polish (patient selector, alerts, citations).
8. Evals + 50-attack injection gate ≥95%.
9. Dual deploy entrypoints (AgentCore + Vertex).
