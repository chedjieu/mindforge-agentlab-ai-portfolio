"""Index writers — PostgreSQL metadata + Weaviate/local vectors."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db import get_connection, ping as db_ping
from pipelines.models import Chunk, ParsedDocument

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
LOCAL_META = ROOT / "data" / "local_store" / "metadata"
LOCAL_VECTORS = ROOT / "data" / "local_store" / "vectors"
COLLECTION = "WidraChunk"

_ACL_BY_HINT: list[tuple[str, str]] = [
    ("executive", "executive"),
    ("comp", "executive"),
    ("finance", "finance_analyst"),
    ("capex", "finance_analyst"),
    ("fcpa", "compliance_officer"),
    ("compliance", "compliance_officer"),
    ("pharmacy", "compliance_officer"),
    ("retention", "compliance_officer"),
]


def infer_acl_policy_name(filename: str, title: str) -> str:
    blob = f"{filename} {title}".lower()
    for hint, policy in _ACL_BY_HINT:
        if hint in blob:
            return policy
    return "general_employee"


class MetadataStore:
    def __init__(self) -> None:
        self.backend = "postgres" if db_ping() else "local"
        if self.backend == "local":
            LOCAL_META.mkdir(parents=True, exist_ok=True)
            logger.warning("Postgres unavailable; using local metadata store")

    def resolve_policy_id(self, policy_name: str) -> str | None:
        if self.backend == "postgres":
            with get_connection() as conn:
                row = conn.execute(
                    "SELECT policy_id FROM acl_policies WHERE name = %s",
                    (policy_name,),
                ).fetchone()
                return str(row[0]) if row else None
        return policy_name

    def create_document(
        self,
        *,
        title: str,
        source_key: str,
        author: str | None,
        acl_policy_name: str,
        metadata: dict[str, Any],
    ) -> str:
        doc_id = str(uuid.uuid4())
        policy_id = self.resolve_policy_id(acl_policy_name)
        if self.backend == "postgres":
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO documents
                      (doc_id, version, title, author, source_key, parse_status, acl_policy_id, metadata)
                    VALUES (%s, 1, %s, %s, %s, 'parsed', %s::uuid, %s::jsonb)
                    """,
                    (
                        doc_id,
                        title,
                        author,
                        source_key,
                        policy_id,
                        json.dumps({**metadata, "acl_policy_name": acl_policy_name}),
                    ),
                )
                conn.commit()
            return doc_id

        path = LOCAL_META / "documents.jsonl"
        record = {
            "doc_id": doc_id,
            "version": 1,
            "title": title,
            "author": author,
            "source_key": source_key,
            "parse_status": "parsed",
            "acl_policy_name": acl_policy_name,
            "metadata": metadata,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        return doc_id

    def write_chunks(self, doc_id: str, chunks: list[Chunk]) -> list[str]:
        chunk_ids: list[str] = []
        if self.backend == "postgres":
            with get_connection() as conn:
                for ch in chunks:
                    cid = str(uuid.uuid4())
                    chunk_ids.append(cid)
                    vector_ref = f"{COLLECTION}:{cid}"
                    conn.execute(
                        """
                        INSERT INTO chunks
                          (chunk_id, doc_id, chunk_index, text, page_start, page_end, is_table, vector_ref, metadata)
                        VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        """,
                        (
                            cid,
                            doc_id,
                            ch.chunk_index,
                            ch.text,
                            ch.page_start,
                            ch.page_end,
                            ch.is_table,
                            vector_ref,
                            json.dumps(ch.metadata),
                        ),
                    )
                conn.commit()
            return chunk_ids

        path = LOCAL_META / "chunks.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            for ch in chunks:
                cid = str(uuid.uuid4())
                chunk_ids.append(cid)
                fh.write(
                    json.dumps(
                        {
                            "chunk_id": cid,
                            "doc_id": doc_id,
                            "chunk_index": ch.chunk_index,
                            "text": ch.text,
                            "page_start": ch.page_start,
                            "page_end": ch.page_end,
                            "is_table": ch.is_table,
                            "vector_ref": f"{COLLECTION}:{cid}",
                            "metadata": ch.metadata,
                        }
                    )
                    + "\n"
                )
        return chunk_ids

    def mark_failed(self, *, title: str, source_key: str, error: str) -> str:
        doc_id = str(uuid.uuid4())
        if self.backend == "postgres":
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO documents
                      (doc_id, title, source_key, parse_status, metadata)
                    VALUES (%s, %s, %s, 'failed', %s::jsonb)
                    """,
                    (doc_id, title, source_key, json.dumps({"error": error})),
                )
                conn.commit()
            return doc_id
        path = LOCAL_META / "documents.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "doc_id": doc_id,
                        "title": title,
                        "source_key": source_key,
                        "parse_status": "failed",
                        "metadata": {"error": error},
                    }
                )
                + "\n"
            )
        return doc_id


class VectorStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = None
        self.backend = "local"
        self._init()

    def _init(self) -> None:
        try:
            import time

            import weaviate
            from weaviate.classes.config import Configure, DataType, Property

            client = weaviate.connect_to_custom(
                http_host="localhost",
                http_port=8081,
                http_secure=False,
                grpc_host="localhost",
                grpc_port=50051,
                grpc_secure=False,
                skip_init_checks=True,
            )
            # Wait briefly for single-node readiness ("leader not found" on cold start)
            last_exc: Exception | None = None
            for _ in range(8):
                try:
                    if not client.collections.exists(COLLECTION):
                        client.collections.create(
                            name=COLLECTION,
                            vectorizer_config=Configure.Vectorizer.none(),
                            properties=[
                                Property(name="chunk_id", data_type=DataType.TEXT),
                                Property(name="doc_id", data_type=DataType.TEXT),
                                Property(name="text", data_type=DataType.TEXT),
                                Property(name="title", data_type=DataType.TEXT),
                                Property(name="page_start", data_type=DataType.INT),
                                Property(name="page_end", data_type=DataType.INT),
                                Property(name="is_table", data_type=DataType.BOOL),
                                Property(name="acl_policy_name", data_type=DataType.TEXT),
                                Property(name="filename", data_type=DataType.TEXT),
                            ],
                        )
                    last_exc = None
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    time.sleep(2)
            if last_exc is not None:
                raise last_exc
            self.client = client
            self.backend = "weaviate"
            logger.info("VectorStore using Weaviate at %s", self.settings.weaviate_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Weaviate unavailable (%s); using local vector store", exc)
            LOCAL_VECTORS.mkdir(parents=True, exist_ok=True)
            self.backend = "local"

    def upsert(
        self,
        *,
        doc_id: str,
        title: str,
        acl_policy_name: str,
        chunks: list[Chunk],
        chunk_ids: list[str],
    ) -> int:
        if self.backend == "weaviate" and self.client is not None:
            col = self.client.collections.get(COLLECTION)
            with col.batch.dynamic() as batch:
                for ch, cid in zip(chunks, chunk_ids, strict=True):
                    if ch.embedding is None:
                        continue
                    batch.add_object(
                        properties={
                            "chunk_id": cid,
                            "doc_id": doc_id,
                            "text": ch.text,
                            "title": title,
                            "page_start": ch.page_start,
                            "page_end": ch.page_end,
                            "is_table": ch.is_table,
                            "acl_policy_name": acl_policy_name,
                            "filename": ch.metadata.get("filename", ""),
                        },
                        vector=ch.embedding,
                        uuid=uuid.UUID(cid),
                    )
            return len(chunk_ids)

        path = LOCAL_VECTORS / "vectors.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            for ch, cid in zip(chunks, chunk_ids, strict=True):
                fh.write(
                    json.dumps(
                        {
                            "chunk_id": cid,
                            "doc_id": doc_id,
                            "title": title,
                            "text": ch.text,
                            "page_start": ch.page_start,
                            "page_end": ch.page_end,
                            "is_table": ch.is_table,
                            "acl_policy_name": acl_policy_name,
                            "filename": ch.metadata.get("filename", ""),
                            "embedding": ch.embedding,
                        }
                    )
                    + "\n"
                )
        return len(chunk_ids)

    def close(self) -> None:
        if self.client is not None:
            try:
                self.client.close()
            except Exception:  # noqa: BLE001
                pass


class JobTracker:
    def __init__(self) -> None:
        self.backend = "postgres" if db_ping() else "local"
        if self.backend == "local":
            LOCAL_META.mkdir(parents=True, exist_ok=True)

    def start(self, source_path: str, docs_total: int) -> str:
        job_id = str(uuid.uuid4())
        if self.backend == "postgres":
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO ingest_jobs
                      (job_id, source_path, status, docs_total, docs_done, started_at)
                    VALUES (%s, %s, 'running', %s, 0, now())
                    """,
                    (job_id, source_path, docs_total),
                )
                conn.commit()
            return job_id
        path = LOCAL_META / "ingest_jobs.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "job_id": job_id,
                        "source_path": source_path,
                        "status": "running",
                        "docs_total": docs_total,
                        "docs_done": 0,
                    }
                )
                + "\n"
            )
        return job_id

    def progress(self, job_id: str, docs_done: int) -> None:
        if self.backend == "postgres":
            with get_connection() as conn:
                conn.execute(
                    "UPDATE ingest_jobs SET docs_done = %s WHERE job_id = %s::uuid",
                    (docs_done, job_id),
                )
                conn.commit()
            return
        # Local: rewrite not required for demo; append progress event
        path = LOCAL_META / "ingest_jobs.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"job_id": job_id, "docs_done": docs_done, "event": "progress"}) + "\n")

    def finish(self, job_id: str, *, status: str = "complete", error: str | None = None) -> None:
        if self.backend == "postgres":
            with get_connection() as conn:
                conn.execute(
                    """
                    UPDATE ingest_jobs
                    SET status = %s, error_message = %s, finished_at = now()
                    WHERE job_id = %s::uuid
                    """,
                    (status, error, job_id),
                )
                conn.commit()
            return
        path = LOCAL_META / "ingest_jobs.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps({"job_id": job_id, "status": status, "error_message": error, "event": "finish"})
                + "\n"
            )


def index_document(
    doc: ParsedDocument,
    chunks: list[Chunk],
    *,
    source_key: str,
    meta_store: MetadataStore | None = None,
    vector_store: VectorStore | None = None,
) -> tuple[str, int]:
    meta_store = meta_store or MetadataStore()
    vector_store = vector_store or VectorStore()
    acl = infer_acl_policy_name(Path(doc.path).name, doc.title)
    doc_id = meta_store.create_document(
        title=doc.title,
        source_key=source_key,
        author=doc.metadata.get("author"),
        acl_policy_name=acl,
        metadata=doc.metadata,
    )
    chunk_ids = meta_store.write_chunks(doc_id, chunks)
    vector_store.upsert(
        doc_id=doc_id,
        title=doc.title,
        acl_policy_name=acl,
        chunks=chunks,
        chunk_ids=chunk_ids,
    )
    return doc_id, len(chunk_ids)
