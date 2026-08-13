"""Async-capable ingestion: parse → chunk → embed → register evidence → graph."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.graph.store import graph_store
from app.ingestion.chunking import chunk_checksum, chunk_document
from app.ingestion.intelligence import authority_score, classify_source, parse_version_label
from app.ingestion.pdf_io import parse_bytes
from app.llm import get_embeddings
from app.security.injection import scan_text
from app.storage.objects import ObjectStore
from app.storage.repo import Store, new_id
from app.storage.schema import (
    DocumentRow,
    DocumentVersionRow,
    EvidenceChunkRow,
    IngestionJobRow,
)

logger = logging.getLogger(__name__)


def enqueue_ingest(
    session: Session,
    tenant_id: str,
    project_id: str,
    filename: str,
    data: bytes,
    *,
    title: str | None = None,
    authority_tier: str | None = None,
    publisher: str = "",
    version_number: str | None = None,
    effective_date: str = "",
    supersedes_version_id: str = "",
    object_store: ObjectStore | None = None,
) -> tuple[DocumentRow, DocumentVersionRow, IngestionJobRow]:
    store = Store(session, tenant_id)
    dtype, tier = classify_source(filename, title or filename, authority_tier)
    doc_id = new_id("doc")
    ver_id = new_id("ver")
    key = f"{tenant_id}/{doc_id}/{ver_id}/{Path(filename).name}"
    (object_store or ObjectStore()).put(key, data)
    parsed = parse_bytes(filename, data)
    doc = DocumentRow(
        id=doc_id,
        tenant_id=tenant_id,
        project_id=project_id,
        title=title or Path(filename).stem,
        document_type=dtype,
        authority_tier=tier,
        publisher=publisher,
        source_uri=key,
    )
    version = DocumentVersionRow(
        id=ver_id,
        tenant_id=tenant_id,
        document_id=doc_id,
        version_number=version_number or parse_version_label(filename),
        effective_date=effective_date,
        supersedes_version_id=supersedes_version_id,
        checksum=parsed.checksum,
        object_key=key,
        page_count=len(parsed.pages),
        ingestion_status="queued",
        ocr_required="true" if parsed.ocr_required else "false",
    )
    job = IngestionJobRow(
        id=new_id("job"),
        tenant_id=tenant_id,
        version_id=ver_id,
        status="queued",
    )
    session.add_all([doc, version, job])
    store.audit("document.uploaded", ver_id, "system", "document", doc_id)
    return doc, version, job


def process_job(session: Session, job_id: str) -> None:
    job = session.get(IngestionJobRow, job_id)
    if job is None:
        raise KeyError(job_id)
    job.attempts += 1
    job.status = "running"
    session.flush()
    try:
        _ingest_version(session, job.tenant_id, job.version_id)
        job.status = "completed"
        job.error = ""
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion failed for %s", job_id)
        job.status = "failed"
        job.error = str(exc)[:2000]
        raise


def _ingest_version(session: Session, tenant_id: str, version_id: str) -> None:
    version = session.get(DocumentVersionRow, version_id)
    doc = session.get(DocumentRow, version.document_id) if version else None
    if not version or not doc or doc.tenant_id != tenant_id:
        raise RuntimeError("version/tenant mismatch")
    if version.ocr_required == "true":
        version.ingestion_status = "ocr_required"
        return
    data = ObjectStore().get(version.object_key)
    filename = Path(version.object_key).name
    parsed = parse_bytes(filename, data)
    drafts = chunk_document(parsed)
    embeddings = get_embeddings().embed_documents([c.text for c in drafts]) if drafts else []
    graph = graph_store()
    graph.upsert_document(
        tenant_id=tenant_id,
        document_id=doc.id,
        title=doc.title,
        version_id=version.id,
        version_number=version.version_number,
        authority_tier=doc.authority_tier,
        supersedes_version_id=version.supersedes_version_id or None,
    )
    for draft, emb in zip(drafts, embeddings, strict=True):
        scan = scan_text(draft.text)
        cid = new_id("chk")
        session.add(
            EvidenceChunkRow(
                id=cid,
                tenant_id=tenant_id,
                document_id=doc.id,
                version_id=version.id,
                page_number=draft.page_number,
                section=draft.section,
                parent_section=draft.parent_section,
                text=draft.text,
                embedding_json=json.dumps(emb),
                authority_tier=doc.authority_tier,
                authority_score=authority_score(doc.authority_tier),
                effective_date=version.effective_date,
                checksum=chunk_checksum(draft.text),
                token_count=len(draft.text.split()),
            )
        )
        graph.upsert_chunk(
            tenant_id=tenant_id,
            document_id=doc.id,
            version_id=version.id,
            chunk_id=cid,
            section=draft.section,
            page=draft.page_number,
            injection_flagged=scan.flagged,
        )
    version.ingestion_status = "indexed"
    version.page_count = len(parsed.pages)


def process_next_job(session: Session) -> bool:
    job = session.scalar(
        select(IngestionJobRow)
        .where(IngestionJobRow.status == "queued")
        .order_by(IngestionJobRow.created_at.asc())
    )
    if job is None:
        return False
    process_job(session, job.id)
    return True
