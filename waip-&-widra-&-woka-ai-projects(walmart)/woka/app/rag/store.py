"""Load indexed chunks for hybrid search (Postgres / local / Weaviate vectors)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.db import get_connection, ping as db_ping

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
LOCAL_META = ROOT / "data" / "local_store" / "metadata"
LOCAL_VECTORS = ROOT / "data" / "local_store" / "vectors"


@dataclass
class IndexedChunk:
    chunk_id: str
    doc_id: str
    title: str
    text: str
    page_start: int = 0
    page_end: int = 0
    is_table: bool = False
    acl_policy_name: str = "general_employee"
    department: str = ""
    region: str = "US"
    confidentiality: str = "internal"
    filename: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    tokens: set[str] = field(default_factory=set)
    vector: list[float] = field(default_factory=list)


_CACHE: list[IndexedChunk] | None = None


def _load_vectors_local() -> dict[str, list[float]]:
    path = LOCAL_VECTORS / "vectors.jsonl"
    out: dict[str, list[float]] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        cid = row.get("chunk_id")
        emb = row.get("embedding")
        if cid and emb:
            out[str(cid)] = emb
    return out


def _load_vectors_weaviate(chunk_ids: list[str]) -> dict[str, list[float]]:
    if not chunk_ids:
        return {}
    try:
        from pipelines.index import VectorStore

        vs = VectorStore()
        if vs.backend != "weaviate" or vs.client is None:
            vs.close()
            return {}
        col = vs.client.collections.get("WokaChunk")
        out: dict[str, list[float]] = {}
        for cid in chunk_ids:
            try:
                obj = col.query.fetch_object_by_id(cid, include_vector=True)
                if obj is None:
                    continue
                vec = obj.vector
                if isinstance(vec, dict):
                    vec = vec.get("default") or next(iter(vec.values()), None)
                if vec:
                    out[cid] = list(vec)
            except Exception:  # noqa: BLE001
                continue
        vs.close()
        return out
    except Exception as exc:  # noqa: BLE001
        logger.debug("Weaviate vector load skipped: %s", exc)
        return {}


def _rows_from_postgres() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with get_connection() as conn:
        cur = conn.execute(
            """
            SELECT c.chunk_id::text, c.doc_id::text, c.text, c.page_start, c.page_end,
                   c.is_table, c.metadata, d.title, COALESCE(p.name, 'general_employee') AS acl_policy_name
            FROM chunks c
            JOIN documents d ON d.doc_id = c.doc_id
            LEFT JOIN acl_policies p ON p.policy_id = d.acl_policy_id
            WHERE d.parse_status = 'parsed'
            """
        )
        for r in cur.fetchall():
            meta = r[6] if isinstance(r[6], dict) else json.loads(r[6] or "{}")
            rows.append(
                {
                    "chunk_id": r[0],
                    "doc_id": r[1],
                    "text": r[2],
                    "page_start": r[3] or 0,
                    "page_end": r[4] or 0,
                    "is_table": bool(r[5]),
                    "metadata": meta,
                    "title": r[7],
                    "acl_policy_name": r[8],
                }
            )
    return rows


def _rows_from_local() -> list[dict[str, Any]]:
    docs_path = LOCAL_META / "documents.jsonl"
    chunks_path = LOCAL_META / "chunks.jsonl"
    if not chunks_path.exists():
        return []
    doc_acl: dict[str, str] = {}
    doc_title: dict[str, str] = {}
    if docs_path.exists():
        for line in docs_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            d = json.loads(line)
            if d.get("parse_status") and d.get("parse_status") != "parsed":
                continue
            doc_acl[d["doc_id"]] = d.get("acl_policy_name") or "general_employee"
            doc_title[d["doc_id"]] = d.get("title") or ""
    rows: list[dict[str, Any]] = []
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        c = json.loads(line)
        doc_id = c["doc_id"]
        rows.append(
            {
                "chunk_id": c["chunk_id"],
                "doc_id": doc_id,
                "text": c["text"],
                "page_start": c.get("page_start") or 0,
                "page_end": c.get("page_end") or 0,
                "is_table": bool(c.get("is_table")),
                "metadata": c.get("metadata") or {},
                "title": doc_title.get(doc_id, ""),
                "acl_policy_name": doc_acl.get(doc_id, "general_employee"),
            }
        )
    return rows


def load_index(force: bool = False) -> list[IndexedChunk]:
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE

    rows = _rows_from_postgres() if db_ping() else _rows_from_local()
    if not rows:
        rows = _rows_from_local()

    local_vecs = _load_vectors_local()
    missing = [r["chunk_id"] for r in rows if r["chunk_id"] not in local_vecs]
    weav_vecs = _load_vectors_weaviate(missing) if missing else {}
    vectors = {**weav_vecs, **local_vecs}

    import re

    chunks: list[IndexedChunk] = []
    for r in rows:
        meta = r.get("metadata") or {}
        text = r["text"]
        cid = r["chunk_id"]
        chunks.append(
            IndexedChunk(
                chunk_id=cid,
                doc_id=r["doc_id"],
                title=r.get("title") or meta.get("filename") or "",
                text=text,
                page_start=int(r.get("page_start") or 0),
                page_end=int(r.get("page_end") or 0),
                is_table=bool(r.get("is_table")),
                acl_policy_name=r.get("acl_policy_name") or "general_employee",
                department=str(meta.get("department") or ""),
                region=str(meta.get("region") or "US"),
                confidentiality=str(meta.get("confidentiality") or "internal"),
                filename=str(meta.get("filename") or ""),
                metadata=meta,
                tokens={t for t in re.findall(r"[a-z0-9\-]+", text.lower()) if len(t) > 1},
                vector=list(vectors.get(cid) or []),
            )
        )

    # Embed any missing vectors with fake/current embeddings gateway
    need = [c for c in chunks if not c.vector]
    if need:
        from app.llm import get_embeddings

        emb = get_embeddings()
        vecs = emb.embed_documents([c.text for c in need])
        for c, v in zip(need, vecs, strict=True):
            c.vector = v

    _CACHE = chunks
    logger.info("Loaded %d indexed chunks for retrieval", len(chunks))
    return chunks


def reset_index_cache() -> None:
    global _CACHE
    _CACHE = None
