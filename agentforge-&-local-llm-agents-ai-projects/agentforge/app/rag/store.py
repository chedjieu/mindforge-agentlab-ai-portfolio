from __future__ import annotations

from typing import Any

import chromadb

from app.config import Settings, get_settings


def get_chroma_client(settings: Settings | None = None) -> Any:
    settings = settings or get_settings()
    settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(settings.chroma_path))


def get_or_create_collection(
    client: Any,
    name: str,
    reset: bool = False,
) -> Any:
    if reset:
        try:
            client.delete_collection(name)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def collection_count(name: str, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    client = get_chroma_client(settings)
    try:
        collection = client.get_collection(name)
        return collection.count()
    except Exception:
        return 0
