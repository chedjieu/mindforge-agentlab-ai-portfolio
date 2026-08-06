"""Ingest Lilian Weng blog posts into ChromaDB."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import Settings, get_settings
from src.rag.vectorstore import add_documents, collection_count

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (compatible; AgenticRAGBot/1.0; +https://github.com/local/agentic-rag)"
)


def load_urls(urls_file: str | Path) -> list[str]:
    path = Path(urls_file)
    if not path.exists():
        raise FileNotFoundError(f"URL list not found: {path}")
    urls: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            urls.append(line)
    return urls


def _extract_title(soup: BeautifulSoup, url: str) -> str:
    for selector in ("article h1", "h1.entry-title", "h1", "title"):
        node = soup.select_one(selector)
        if node and node.get_text(strip=True):
            title = node.get_text(strip=True)
            title = re.sub(r"\s*\|\s*Lil'?ian Weng.*$", "", title, flags=re.I)
            return title.strip() or url
    return urlparse(url).path.rstrip("/").split("/")[-1] or url


def _extract_article_text(soup: BeautifulSoup) -> str:
    article = (
        soup.select_one("article.post")
        or soup.select_one("article")
        or soup.select_one("main")
        or soup.body
    )
    if article is None:
        return ""

    for tag in article.select("script, style, nav, footer, .share, .related"):
        tag.decompose()

    text = article.get_text(separator="\n", strip=True)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_document(url: str, client: httpx.Client) -> Document | None:
    try:
        response = client.get(url, follow_redirects=True, timeout=60.0)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None

    soup = BeautifulSoup(response.text, "lxml")
    title = _extract_title(soup, url)
    text = _extract_article_text(soup)
    if not text or len(text) < 200:
        logger.warning("Insufficient content extracted from %s", url)
        return None

    return Document(
        page_content=text,
        metadata={
            "title": title,
            "url": url,
            "source": url,
        },
    )


def load_documents(urls: list[str]) -> list[Document]:
    documents: list[Document] = []
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
    with httpx.Client(headers=headers) as client:
        for url in urls:
            logger.info("Fetching %s", url)
            doc = fetch_document(url, client)
            if doc:
                documents.append(doc)
                logger.info("Loaded '%s' (%d chars)", doc.metadata["title"], len(doc.page_content))
    return documents


def chunk_documents(
    documents: list[Document],
    settings: Settings | None = None,
) -> list[Document]:
    settings = settings or get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


def run_ingest(settings: Settings | None = None) -> dict:
    """Full ingest pipeline: load URLs → chunk → embed → Chroma."""
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    urls = load_urls(settings.urls_file)
    logger.info("Ingesting %d URLs from %s", len(urls), settings.urls_file)

    documents = load_documents(urls)
    if not documents:
        raise RuntimeError("No documents were successfully loaded.")

    chunks = chunk_documents(documents, settings)
    logger.info("Split into %d chunks", len(chunks))

    count = add_documents(chunks, settings)
    result = {
        "urls_total": len(urls),
        "documents_loaded": len(documents),
        "chunks_indexed": len(chunks),
        "collection_count": count,
        "collection": settings.chroma_collection,
        "chroma_dir": settings.chroma_dir,
        "failed_urls": [u for u in urls if u not in {d.metadata["url"] for d in documents}],
    }
    logger.info("Ingest complete: %s", result)
    return result


def main() -> None:
    result = run_ingest()
    print("Ingest summary:")
    for key, value in result.items():
        print(f"  {key}: {value}")
    print(f"Current collection size: {collection_count()}")


if __name__ == "__main__":
    main()
