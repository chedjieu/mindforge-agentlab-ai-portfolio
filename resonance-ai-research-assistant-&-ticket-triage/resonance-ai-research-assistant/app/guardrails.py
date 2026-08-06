"""Citation guardrails — detect URLs in reports and validate against research findings."""

from __future__ import annotations

import re

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
URL_RE = re.compile(r"https?://[^\s\"'\)\]>]+")


def extract_urls(text: str) -> set[str]:
    """Return URLs from markdown links and bare https://... patterns."""
    urls: set[str] = set()
    for _label, url in MARKDOWN_LINK_RE.findall(text):
        url = url.strip()
        if url:
            urls.add(url)
    urls.update(URL_RE.findall(text))
    return urls


def validate_citations(report: str, allowed_urls: set[str]) -> tuple[bool, list[str]]:
    """Return (ok, bad_urls) where ok is True when every cited URL is allowed."""
    bad_urls: list[str] = []
    for url in extract_urls(report):
        if url not in allowed_urls and url not in bad_urls:
            bad_urls.append(url)
    return (len(bad_urls) == 0, bad_urls)
