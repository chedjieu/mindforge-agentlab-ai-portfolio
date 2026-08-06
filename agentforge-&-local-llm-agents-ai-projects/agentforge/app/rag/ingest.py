from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from app.config import Settings, get_settings
from app.observability.tracing import traced_span
from app.rag.embeddings import OllamaEmbedder
from app.rag.store import get_chroma_client, get_or_create_collection


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        start += chunk_size - overlap
    return chunks


def extract_pdf_pages(pdf_path: Path) -> list[tuple[int, str]]:
    reader = PdfReader(str(pdf_path))
    pages: list[tuple[int, str]] = []
    for idx, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if text:
            pages.append((idx, text))
    return pages


def resolve_pdf_path(pdf_path: str | None, settings: Settings) -> Path:
    if pdf_path:
        path = Path(pdf_path)
        if not path.is_absolute():
            candidate = settings.assets_dir / path
            path = candidate if candidate.exists() else path
    else:
        pdfs = sorted(settings.assets_dir.glob("*.pdf"))
        if not pdfs:
            raise FileNotFoundError(
                f"No PDF found in {settings.assets_dir}. "
                "Place a PDF there or pass pdf_path."
            )
        path = pdfs[0]
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    return path.resolve()


def ingest_pdf(pdf_path: str | None = None, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    settings.ensure_dirs()
    path = resolve_pdf_path(pdf_path, settings)

    with traced_span("rag.ingest_pdf", {"source": str(path)}):
        pages = extract_pdf_pages(path)
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []
        ids: list[str] = []

        for page_num, page_text in pages:
            pieces = chunk_text(
                page_text,
                settings.chunk_size,
                settings.chunk_overlap,
            )
            for chunk_idx, chunk in enumerate(pieces):
                doc_id = f"{path.stem}-p{page_num}-c{chunk_idx}"
                ids.append(doc_id)
                documents.append(chunk)
                metadatas.append(
                    {
                        "source": path.name,
                        "page": page_num,
                        "chunk_id": chunk_idx,
                    }
                )

        if not documents:
            raise ValueError(f"No extractable text in {path}")

        embedder = OllamaEmbedder(settings)
        embeddings = embedder.embed_documents(documents)

        client = get_chroma_client(settings)
        collection = get_or_create_collection(
            client,
            settings.rag_collection,
            reset=True,
        )
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        return {
            "status": "ok",
            "documents_indexed": len(documents),
            "collection": settings.rag_collection,
            "source": path.name,
        }
