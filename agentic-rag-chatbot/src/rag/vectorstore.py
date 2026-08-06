"""ChromaDB vector store helpers."""

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import Settings, get_settings
from src.rag.embeddings import get_embeddings


def get_vectorstore(settings: Settings | None = None) -> Chroma:
    settings = settings or get_settings()
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=get_embeddings(settings),
        persist_directory=settings.chroma_dir,
    )


def collection_count(settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    store = get_vectorstore(settings)
    try:
        return store._collection.count()  # noqa: SLF001
    except Exception:
        return 0


def add_documents(documents: list[Document], settings: Settings | None = None) -> int:
    """Replace the collection with the given documents and return the count."""
    settings = settings or get_settings()
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)

    store = get_vectorstore(settings)
    # Clear existing collection for a clean re-ingest
    try:
        ids = store.get()["ids"]
        if ids:
            store.delete(ids=ids)
    except Exception:
        pass

    if documents:
        store.add_documents(documents)
    return collection_count(settings)
