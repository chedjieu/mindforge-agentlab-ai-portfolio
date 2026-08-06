# WOKA project prompts (implementation order)

1. Lock AS_BUILT + SYSTEM_DESIGN + ARCHITECTURE + IMPLEMENTATION_PLAN (done).
2. Scaffold package, Docker Compose, Postgres schema + SQL seeds, fake LLM, FastAPI stubs (done).
3. Ingestion: classify → parse → chunk → embed → index (MinIO + Weaviate + Postgres) (done).
4. Security Agent + ACL seeds + RBAC leak tests (100% pass) (done).
5. Hybrid retrieval + GraphRAG + Retrieval Agent (done).
6. Multi-agent UC-1 orchestrator (SQL + internet + merge + citation) + streaming UI (done).
7. LLM-as-judge evals + injection ≥95% + LangSmith + audit APIs (done).
8. Scale ingest + Pinecone/S3 + AgentCore/Vertex deploy entrypoints (done).
