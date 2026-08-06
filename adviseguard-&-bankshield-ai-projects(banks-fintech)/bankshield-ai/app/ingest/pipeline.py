"""Chunk corpus → embed → Chroma upsert → optional Neo4j seed load."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS = ROOT / "data" / "corpus"
DEFAULT_CHROMA = ROOT / "data" / "chroma"
COLLECTION_NAME = "bankshield_chunks"


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1]) or {}
            return dict(meta), parts[2].strip()
    return {}, text


def load_documents() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for path in sorted(CORPUS.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        domain = meta.get("domain") or path.parent.name
        docs.append(
            {
                "path": str(path.relative_to(ROOT)),
                "domain": domain,
                "title": meta.get("title") or path.stem,
                "text": body,
                "metadata": meta,
            }
        )
    return docs


def chunk_documents(docs: list[dict[str, Any]], *, max_chars: int = 900) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for doc in docs:
        text = doc["text"]
        paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        buf = ""
        idx = 0
        for para in paras or [text]:
            if len(buf) + len(para) + 1 > max_chars and buf:
                cid = hashlib.sha1(f"{doc['path']}:{idx}".encode()).hexdigest()[:16]
                chunks.append(
                    {
                        "id": cid,
                        "text": buf.strip(),
                        "metadata": {
                            "domain": doc["domain"],
                            "title": doc["title"],
                            "source": doc["path"],
                            "chunk": idx,
                        },
                    }
                )
                idx += 1
                buf = para
            else:
                buf = f"{buf}\n\n{para}".strip()
        if buf.strip():
            cid = hashlib.sha1(f"{doc['path']}:{idx}".encode()).hexdigest()[:16]
            chunks.append(
                {
                    "id": cid,
                    "text": buf.strip(),
                    "metadata": {
                        "domain": doc["domain"],
                        "title": doc["title"],
                        "source": doc["path"],
                        "chunk": idx,
                    },
                }
            )
    return chunks


def embed_and_upsert(chunks: list[dict[str, Any]]) -> int:
    import chromadb

    from app.llm import get_embeddings

    if not os.getenv("BANKSHIELD_EMBEDDINGS"):
        os.environ["BANKSHIELD_EMBEDDINGS"] = "fake"

    persist = Path(os.getenv("BANKSHIELD_CHROMA_DIR") or DEFAULT_CHROMA)
    persist.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist))
    # Recreate for idempotent local demos
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    emb = get_embeddings()

    batch = 32
    total = 0
    for i in range(0, len(chunks), batch):
        part = chunks[i : i + batch]
        vectors = emb.embed_documents([c["text"] for c in part])
        collection.upsert(
            ids=[c["id"] for c in part],
            documents=[c["text"] for c in part],
            metadatas=[c["metadata"] for c in part],
            embeddings=vectors,
        )
        total += len(part)
    return total


def run_ingest() -> dict[str, int]:
    docs = load_documents()
    chunks = chunk_documents(docs)
    n = embed_and_upsert(chunks)
    kg_edges = 0
    try:
        from app.tools.neo4j_graph import load_kg_seeds_to_neo4j

        kg_edges = load_kg_seeds_to_neo4j()
    except Exception:
        kg_edges = 0
    return {"documents": len(docs), "chunks": n, "kg_edges": kg_edges}


def main() -> None:
    stats = run_ingest()
    print(f"Ingest complete: {stats}")


if __name__ == "__main__":
    main()
