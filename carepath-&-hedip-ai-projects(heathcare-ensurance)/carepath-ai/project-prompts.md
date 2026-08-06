# CarePath AI project prompts (implementation order)

1. Lock AS_BUILT + SYSTEM_DESIGN + ARCHITECTURE (done).
2. Scaffold package, state, firewall, fake LLM, FastAPI console on :8007.
3. Hybrid RAG + Neo4j/JSONL GraphRAG + corpus / patient / protocol seeds.
4. Procedural + episodic + semantic memory modules.
5. Supervisor + extract / med-check / generate / preference / evaluate workers.
6. HITL interrupt + plan_publish audit log.
7. Clinician console UI (patient selector, step log, citations, alerts).
8. Dual deploy entrypoints (AgentCore + Vertex).
9. Evals + 50-attack injection gate ≥95%.
