# WIDRA project prompts (implementation order)

1. Lock AS_BUILT + SYSTEM_DESIGN + ARCHITECTURE + IMPLEMENTATION_PLAN (done).
2. Scaffold package, Docker Compose, Postgres schema, fake LLM, FastAPI stub (done).
3. Ingestion pipeline: PDF parse → chunk → embed → index (MinIO + Weaviate + Postgres) (done).
4. Auth Agent + ACL seed data + RBAC leak tests (100% pass).
5. Hybrid retrieval + rerank + Retrieval Agent.
6. Answer Agent + table fact extractor + citation assembly + streaming UI.
7. LangGraph supervisor wiring + Observability Agent.
8. Eval harness (retrieval, groundedness, citations) + injection gate ≥ 95%.
9. Scale ingest (batch checkpointing) + Pinecone/S3 prod adapters + deploy entrypoints.
