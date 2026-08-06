"""Fetch and extract plain text from a URL."""

from __future__ import annotations

import os

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool

_MAX_CHARS = 8000
_TIMEOUT = 10.0
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@tool
def fetch_url(url: str) -> str:
    """Fetch a web page and return its plain-text content. Use this when you need the full text of a specific URL from search results."""
    if os.getenv("RAIRA_MODEL", "").strip() == "fake":
        return f"[Source: {url}]\nOffline mock page content for eval/demo mode."

    headers = {"User-Agent": _USER_AGENT}
    with httpx.Client(timeout=_TIMEOUT, headers=headers, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS]

    return f"[Source: {url}]\n{text}"


if __name__ == "__main__":
    snippet = fetch_url.invoke({"url": "https://example.com"})
    print(snippet[:400] + ("..." if len(snippet) > 400 else ""))
