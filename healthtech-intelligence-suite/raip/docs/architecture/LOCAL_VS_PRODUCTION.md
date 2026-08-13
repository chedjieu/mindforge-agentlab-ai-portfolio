# Local vs production matrix

| Subsystem | Local implementation | Production implementation | Known limitations | Migration path |
|-----------|----------------------|---------------------------|-------------------|----------------|
| API | FastAPI `:8011` | Same behind ALB/HTTPS | Single instance | Horizontal replicas; sticky HITL via checkpointer |
| UI | Server-rendered HTML | Same or React later | No npm | Keep until UX requires SPA |
| Metadata DB | SQLite | Postgres | No HA | `RAIP_DATABASE_URL` |
| Vectors | JSON embeddings + cosine | pgvector / OpenSearch / Pinecone | No ANN at scale | `VectorStore` adapter; keep chunk IDs |
| Keyword | rank-bm25 in-process | OpenSearch BM25 | Memory bound | Same fusion (RRF) interface |
| Graph | In-memory / JSONL | Neo4j | Process-local | `NEO4J_URI` |
| Objects | Local disk | S3 / GCS | No replication | `ObjectStore` adapter |
| Queue | SQL job rows | SQS / Pub/Sub | Polling worker | Same job schema |
| Models | `fake` | Bedrock / Vertex | Fake is heuristic | Env vars only |
| Auth | Headers | OIDC | Not an IdP | `Principal` already isolated |
| OCR | Detect only | Textract / Tesseract | Scanned PDFs blocked | Worker flag `ocr_required` |
| Malware | MIME/size/hash | ClamAV / GuardDuty | Not a scanner | Sidecar before `put` |
| Secrets | `.env` | SM / GSM | Don't commit `.env` | IAM roles |
| Observability | Logs + `/metrics` | OTel collector + APM | No hosted dashboards | Same field names |
| Checkpointer | MemorySaver | PostgresSaver | HITL lost on restart in memory mode | `RAIP_MEMORY=postgres` |
