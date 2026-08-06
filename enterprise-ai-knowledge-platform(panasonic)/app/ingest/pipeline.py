"""Knowledge ingest: load → chunk → embed/upsert → KG seeds."""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CORPUS = ROOT / "data" / "corpus"
DEFAULT_KG = ROOT / "data" / "kg"
DEFAULT_CHROMA = ROOT / "data" / "chroma"
COLLECTION_NAME = "egkp_chunks"


@dataclass
class Document:
    doc_id: str
    domain: str
    text: str
    path: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


def _parse_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\n")
    return meta, body


def load_documents(corpus_root: str | Path | None = None) -> list[Document]:
    """Load markdown docs with YAML frontmatter from corpus_root."""
    root = Path(corpus_root or DEFAULT_CORPUS)
    docs: list[Document] = []
    for path in sorted(root.rglob("*.md")):
        if path.name.upper() == "README.MD":
            continue
        raw = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        doc_id = str(meta.get("doc_id") or path.stem)
        domain = str(meta.get("domain") or path.parent.name)
        acl = meta.get("acl_roles") or []
        if isinstance(acl, str):
            acl = [a.strip() for a in acl.strip("[]").split(",") if a.strip()]
        entities = meta.get("entities") or []
        if isinstance(entities, str):
            entities = [e.strip() for e in entities.strip("[]").split(",") if e.strip()]
        docs.append(
            Document(
                doc_id=doc_id,
                domain=domain,
                text=body,
                path=str(path),
                metadata={
                    "doc_id": doc_id,
                    "domain": domain,
                    "doc_type": meta.get("doc_type", ""),
                    "plant": meta.get("plant", ""),
                    "acl_roles": list(acl),
                    "effective_date": str(meta.get("effective_date") or ""),
                    "supersedes": str(meta.get("supersedes") or ""),
                    "entities": list(entities),
                    "source_path": str(path.relative_to(root)).replace("\\", "/"),
                },
            )
        )
    return docs


def chunk_documents(docs: list[Document], max_chars: int = 1200) -> list[Chunk]:
    """Heading-aware chunking; preserve metadata + acl_roles."""
    chunks: list[Chunk] = []
    heading_re = re.compile(r"(?m)^(#{1,3}\s+.+)$")

    for doc in docs:
        text = doc.text.strip()
        if not text:
            continue
        # Split on markdown headings, keeping headings with following body.
        parts = heading_re.split(text)
        sections: list[str] = []
        if parts and parts[0].strip() and not parts[0].startswith("#"):
            sections.append(parts[0].strip())
        i = 1
        while i < len(parts):
            heading = parts[i].strip()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            sections.append(f"{heading}\n\n{body}".strip() if body else heading)
            i += 2
        if not sections:
            sections = [text]

        for idx, section in enumerate(sections):
            pieces = _split_long(section, max_chars)
            for j, piece in enumerate(pieces):
                digest = hashlib.sha1(f"{doc.doc_id}:{idx}:{j}:{piece[:80]}".encode()).hexdigest()[:12]
                chunk_id = f"{doc.doc_id}::{idx}-{j}::{digest}"
                meta = dict(doc.metadata)
                meta["chunk_index"] = idx
                meta["part"] = j
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc.doc_id,
                        text=piece,
                        metadata=meta,
                    )
                )
    return chunks


def _split_long(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    out: list[str] = []
    paras = re.split(r"\n\s*\n", text)
    buf = ""
    for p in paras:
        if not buf:
            buf = p
        elif len(buf) + 2 + len(p) <= max_chars:
            buf = f"{buf}\n\n{p}"
        else:
            out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    # Hard-split any remaining oversized piece
    final: list[str] = []
    for piece in out:
        if len(piece) <= max_chars:
            final.append(piece)
        else:
            for k in range(0, len(piece), max_chars):
                final.append(piece[k : k + max_chars])
    return final


def embed_and_upsert(chunks: list[Chunk], backend: str | None = None) -> dict[str, Any]:
    """Embed chunks and upsert into the configured vector backend."""
    backend = (backend or os.getenv("EGKP_VECTORS") or "chroma").strip().lower()
    if backend == "chroma":
        return _upsert_chroma(chunks)
    if backend == "pgvector":
        return _upsert_pgvector(chunks)
    raise ValueError(f"Unsupported EGKP_VECTORS backend: {backend!r} (use chroma|pgvector)")


def _upsert_chroma(chunks: list[Chunk]) -> dict[str, Any]:
    import chromadb

    from app.llm import get_embeddings

    persist = Path(os.getenv("EGKP_CHROMA_DIR") or DEFAULT_CHROMA)
    persist.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist))
    # Recreate collection for idempotent local demos
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    emb = get_embeddings()
    texts = [c.text for c in chunks]
    vectors = emb.embed_documents(texts)
    ids = [c.chunk_id for c in chunks]
    metadatas: list[dict[str, Any]] = []
    for c in chunks:
        md = {
            "doc_id": c.doc_id,
            "domain": str(c.metadata.get("domain", "")),
            "doc_type": str(c.metadata.get("doc_type", "")),
            "plant": str(c.metadata.get("plant", "")),
            "acl_roles": json.dumps(c.metadata.get("acl_roles") or []),
            "effective_date": str(c.metadata.get("effective_date", "")),
            "supersedes": str(c.metadata.get("supersedes", "")),
            "entities": json.dumps(c.metadata.get("entities") or []),
            "source_path": str(c.metadata.get("source_path", "")),
        }
        metadatas.append(md)

    batch = 64
    for i in range(0, len(chunks), batch):
        collection.upsert(
            ids=ids[i : i + batch],
            documents=texts[i : i + batch],
            embeddings=vectors[i : i + batch],
            metadatas=metadatas[i : i + batch],
        )
    return {"backend": "chroma", "count": len(chunks), "path": str(persist)}


def _upsert_pgvector(chunks: list[Chunk]) -> dict[str, Any]:
    """Optional pgvector upsert via POSTGRES_DSN."""
    dsn = os.getenv("POSTGRES_DSN")
    if not dsn:
        raise RuntimeError("EGKP_VECTORS=pgvector requires POSTGRES_DSN")

    import psycopg
    from pgvector.psycopg import register_vector

    from app.llm import get_embeddings

    emb = get_embeddings()
    vectors = emb.embed_documents([c.text for c in chunks])
    dim = len(vectors[0]) if vectors else 1024

    with psycopg.connect(dsn) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS egkp_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    domain TEXT,
                    text TEXT NOT NULL,
                    metadata JSONB,
                    embedding vector({dim})
                )
                """
            )
            for c, vec in zip(chunks, vectors, strict=True):
                cur.execute(
                    """
                    INSERT INTO egkp_chunks (chunk_id, doc_id, domain, text, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        doc_id = EXCLUDED.doc_id,
                        domain = EXCLUDED.domain,
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        c.chunk_id,
                        c.doc_id,
                        c.metadata.get("domain"),
                        c.text,
                        json.dumps(c.metadata),
                        vec,
                    ),
                )
        conn.commit()
    return {"backend": "pgvector", "count": len(chunks), "dim": dim}


def load_kg_seeds(neo4j_driver: Any | None = None) -> dict[str, Any]:
    """Load entities/relations into Neo4j with idempotent MERGE.

    If neo4j_driver is None, connect using EGKP_NEO4J_* env vars.
    If Neo4j is unavailable, validate JSONL seeds and return skipped=True.
    """
    ent_path = DEFAULT_KG / "seed_entities.jsonl"
    rel_path = DEFAULT_KG / "seed_relations.jsonl"
    entities = [
        json.loads(line)
        for line in ent_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    relations = [
        json.loads(line)
        for line in rel_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    driver = neo4j_driver
    owns_driver = False
    if driver is None:
        uri = os.getenv("EGKP_NEO4J_URI", "").strip()
        if not uri:
            return {
                "backend": "neo4j",
                "skipped": True,
                "reason": "EGKP_NEO4J_URI unset",
                "entities": len(entities),
                "relations": len(relations),
            }
        from neo4j import GraphDatabase

        user = os.getenv("EGKP_NEO4J_USER", "neo4j")
        password = os.getenv("EGKP_NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(uri, auth=(user, password))
        owns_driver = True

    try:
        with driver.session() as session:
            for e in entities:
                label = re.sub(r"[^A-Za-z0-9_]", "_", e["label"])
                session.run(
                    f"""
                    MERGE (n:`{label}` {{id: $id}})
                    SET n.name = $name, n.label = $label
                    SET n += $props
                    """,
                    id=e["id"],
                    name=e.get("name", e["id"]),
                    label=e["label"],
                    props=e.get("props") or {},
                )
            for r in relations:
                rel = re.sub(r"[^A-Za-z0-9_]", "_", r["rel"])
                session.run(
                    f"""
                    MATCH (a {{id: $src}})
                    MATCH (b {{id: $dst}})
                    MERGE (a)-[rel:`{rel}`]->(b)
                    SET rel += $props
                    """,
                    src=r["src"],
                    dst=r["dst"],
                    props=r.get("props") or {},
                )
    finally:
        if owns_driver and driver is not None:
            driver.close()

    return {
        "backend": "neo4j",
        "skipped": False,
        "entities": len(entities),
        "relations": len(relations),
    }


def run_ingest(
    corpus_root: str | Path | None = None,
    backend: str | None = None,
    load_kg: bool = True,
) -> dict[str, Any]:
    docs = load_documents(corpus_root)
    chunks = chunk_documents(docs)
    vector_result = embed_and_upsert(chunks, backend=backend)
    kg_result: dict[str, Any] = {"skipped": True, "reason": "disabled"}
    if load_kg:
        try:
            kg_result = load_kg_seeds()
        except Exception as exc:
            kg_result = {"skipped": True, "reason": str(exc)}
    return {
        "documents": len(docs),
        "chunks": len(chunks),
        "vectors": vector_result,
        "kg": kg_result,
        "sample_chunk": asdict(chunks[0]) if chunks else None,
    }


def main() -> None:
    # Prefer fake embeddings for local ingest unless explicitly configured.
    if not os.getenv("EGKP_EMBEDDINGS"):
        os.environ["EGKP_EMBEDDINGS"] = "fake"
    result = run_ingest()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
