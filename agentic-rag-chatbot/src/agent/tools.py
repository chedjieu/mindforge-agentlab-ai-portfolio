"""Tools available to the agentic RAG assistant."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from langchain_core.tools import tool

from src.config import get_settings
from src.rag.retriever import (
    format_chunks_for_agent,
    search_knowledge_base,
    unique_sources,
)
from src.rag.vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

# Shared bag so the API layer can collect sources used during a turn
_last_sources: list[dict[str, str]] = []


def reset_turn_state() -> None:
    _last_sources.clear()


def get_turn_sources() -> list[dict[str, str]]:
    return list(_last_sources)


def _merge_sources(new_sources: list[dict[str, str]]) -> None:
    seen = {(s.get("url"), s.get("title")) for s in _last_sources}
    for source in new_sources:
        key = (source.get("url"), source.get("title"))
        if key not in seen:
            _last_sources.append(source)
            seen.add(key)


@tool
def search_knowledge_base_tool(query: str) -> str:
    """Search the Lilian Weng blog knowledge base for passages relevant to the query.
    Always use this first for questions about ML, LLMs, agents, diffusion, prompt
    engineering, transformers, or related research topics covered in the KB.
    """
    settings = get_settings()
    chunks = search_knowledge_base(query, settings=settings)
    _merge_sources(unique_sources(chunks))
    return format_chunks_for_agent(chunks)


@tool
def get_source_summary(url_or_title: str) -> str:
    """Look up metadata and a short snippet for a knowledge-base source by URL or title.
    Use this to confirm citations or list what a specific post covers.
    """
    store = get_vectorstore()
    # Broad fetch then filter locally (Chroma where filter varies by version)
    try:
        raw = store.get(include=["documents", "metadatas"], limit=200)
    except Exception as exc:
        return f"Could not read vector store: {exc}"

    metadatas = raw.get("metadatas") or []
    documents = raw.get("documents") or []
    needle = url_or_title.strip().lower()

    matches: list[dict[str, Any]] = []
    for meta, doc in zip(metadatas, documents):
        meta = meta or {}
        title = str(meta.get("title") or "")
        url = str(meta.get("url") or meta.get("source") or "")
        if needle in title.lower() or needle in url.lower():
            matches.append(
                {
                    "title": title,
                    "url": url,
                    "snippet": (doc or "")[:400],
                }
            )
            if len(matches) >= 3:
                break

    if not matches:
        return f"No KB source matched '{url_or_title}'."

    _merge_sources([{"title": m["title"], "url": m["url"]} for m in matches])
    return json.dumps(matches, indent=2)


def _web_search_serper(query: str, api_key: str) -> str:
    payload = {"q": query, "num": 5}
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    organic = data.get("organic") or []
    if not organic:
        return "No web search results found."

    lines = []
    for i, item in enumerate(organic[:5], start=1):
        lines.append(
            f"[{i}] {item.get('title', 'Untitled')}\n"
            f"URL: {item.get('link', '')}\n"
            f"{item.get('snippet', '')}"
        )
    return "\n\n".join(lines)


def _web_search_duckduckgo(query: str) -> str:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "Web search unavailable: duckduckgo-search is not installed."

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=5))

    if not results:
        return "No web search results found."

    lines = []
    for i, item in enumerate(results, start=1):
        lines.append(
            f"[{i}] {item.get('title', 'Untitled')}\n"
            f"URL: {item.get('href', '')}\n"
            f"{item.get('body', '')}"
        )
    return "\n\n".join(lines)


@tool
def web_search(query: str) -> str:
    """Search the public web for information not covered by the knowledge base.
    Use only when the KB search returns nothing useful, or the user asks about
    current events / topics outside Lilian Weng's posts.
    """
    settings = get_settings()
    try:
        if settings.serper_api_key:
            return _web_search_serper(query, settings.serper_api_key)
        return _web_search_duckduckgo(query)
    except Exception as exc:
        logger.exception("Web search failed")
        return f"Web search failed: {exc}"


def get_agent_tools() -> list:
    return [search_knowledge_base_tool, get_source_summary, web_search]
