from __future__ import annotations

import hashlib
import time
from typing import Any

from app.config import Settings, get_settings
from app.rag.embeddings import OllamaEmbedder
from app.rag.store import get_chroma_client, get_or_create_collection


def remember(
    text: str,
    metadata: dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> str:
    """Persist a durable memory fact into Chroma."""
    settings = settings or get_settings()
    text = text.strip()
    if not text:
        raise ValueError("Cannot store empty memory.")

    embedder = OllamaEmbedder(settings)
    embedding = embedder.embed_query(text)
    client = get_chroma_client(settings)
    collection = get_or_create_collection(client, settings.memory_collection)

    mem_id = hashlib.sha256(f"{time.time_ns()}:{text}".encode("utf-8")).hexdigest()[:24]
    meta = {"kind": "long_term", "ts": time.time()}
    if metadata:
        meta.update({k: str(v) for k, v in metadata.items()})

    collection.add(
        ids=[mem_id],
        documents=[text],
        metadatas=[meta],
        embeddings=[embedding],
    )
    return mem_id


def recall(
    query: str,
    top_k: int = 3,
    settings: Settings | None = None,
) -> list[str]:
    settings = settings or get_settings()
    client = get_chroma_client(settings)
    collection = get_or_create_collection(client, settings.memory_collection)
    if collection.count() == 0:
        return []

    embedder = OllamaEmbedder(settings)
    embedding = embedder.embed_query(query)
    result = collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, collection.count()),
        include=["documents"],
    )
    docs = (result.get("documents") or [[]])[0]
    return [d for d in docs if d]
