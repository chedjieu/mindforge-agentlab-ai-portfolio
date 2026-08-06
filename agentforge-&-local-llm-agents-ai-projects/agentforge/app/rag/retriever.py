from __future__ import annotations

from app.config import Settings, get_settings
from app.observability.tracing import traced_span
from app.rag.embeddings import OllamaEmbedder
from app.rag.store import get_chroma_client, get_or_create_collection
from app.rag.types import RetrievedChunk


def retrieve(
    query: str,
    top_k: int | None = None,
    settings: Settings | None = None,
    collection_name: str | None = None,
) -> list[RetrievedChunk]:
    settings = settings or get_settings()
    top_k = top_k or settings.retrieve_top_k
    name = collection_name or settings.rag_collection

    with traced_span("rag.retrieve", {"top_k": top_k, "collection": name}):
        client = get_chroma_client(settings)
        collection = get_or_create_collection(client, name, reset=False)
        if collection.count() == 0:
            return []

        embedder = OllamaEmbedder(settings)
        query_embedding = embedder.embed_query(query)
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        chunks: list[RetrievedChunk] = []
        for text, meta, distance in zip(documents, metadatas, distances):
            # Chroma cosine distance: lower is better; convert to similarity-like score
            score = 1.0 - float(distance)
            chunks.append(
                RetrievedChunk(
                    text=text or "",
                    score=score,
                    metadata=meta or {},
                )
            )
        return chunks


def format_context(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        parts.append(
            f"[Chunk {idx} | score={chunk.score:.3f} | {chunk.citation}]\n{chunk.text}"
        )
    return "\n\n".join(parts)
