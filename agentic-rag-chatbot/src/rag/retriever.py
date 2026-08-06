"""Semantic retriever over the Chroma knowledge base."""

from dataclasses import dataclass

from langchain_core.documents import Document

from src.config import Settings, get_settings
from src.rag.vectorstore import get_vectorstore


@dataclass
class RetrievedChunk:
    content: str
    title: str
    url: str
    score: float | None = None


def search_knowledge_base(
    query: str,
    *,
    k: int | None = None,
    settings: Settings | None = None,
) -> list[RetrievedChunk]:
    settings = settings or get_settings()
    top_k = k or settings.top_k
    store = get_vectorstore(settings)

    results = store.similarity_search_with_relevance_scores(query, k=top_k)
    chunks: list[RetrievedChunk] = []
    for doc, score in results:
        meta = doc.metadata or {}
        chunks.append(
            RetrievedChunk(
                content=doc.page_content,
                title=meta.get("title") or meta.get("source") or "Untitled",
                url=meta.get("url") or meta.get("source") or "",
                score=float(score) if score is not None else None,
            )
        )
    return chunks


def format_chunks_for_agent(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "No relevant documents found in the knowledge base."

    parts: list[str] = []
    for i, chunk in enumerate(chunks, start=1):
        score_txt = f" (relevance={chunk.score:.3f})" if chunk.score is not None else ""
        parts.append(
            f"[{i}] {chunk.title}{score_txt}\n"
            f"URL: {chunk.url}\n"
            f"{chunk.content}"
        )
    return "\n\n---\n\n".join(parts)


def unique_sources(chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    seen: set[str] = set()
    sources: list[dict[str, str]] = []
    for chunk in chunks:
        key = chunk.url or chunk.title
        if key in seen:
            continue
        seen.add(key)
        sources.append({"title": chunk.title, "url": chunk.url})
    return sources


def docs_to_chunks(docs: list[Document]) -> list[RetrievedChunk]:
    chunks: list[RetrievedChunk] = []
    for doc in docs:
        meta = doc.metadata or {}
        chunks.append(
            RetrievedChunk(
                content=doc.page_content,
                title=meta.get("title") or meta.get("source") or "Untitled",
                url=meta.get("url") or meta.get("source") or "",
            )
        )
    return chunks
