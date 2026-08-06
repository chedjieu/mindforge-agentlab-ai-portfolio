"""Semantic + table-aware chunker."""

from __future__ import annotations

import re

from pipelines.models import Chunk, ParsedDocument

_HEADING = re.compile(r"^(?:[A-Z][A-Za-z0-9 /&\-]{2,60}|#{1,3}\s+.+)$")
_WORD = re.compile(r"\S+")


def _token_count(text: str) -> int:
    return len(_WORD.findall(text))


def _split_prose(text: str, target: int = 500, overlap: int = 80) -> list[str]:
    """Heading-aware recursive split approximating 400–600 tokens."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    sections: list[str] = []
    current: list[str] = []
    for para in paragraphs:
        first = para.splitlines()[0].strip() if para else ""
        if current and _HEADING.match(first) and _token_count("\n".join(current)) > 80:
            sections.append("\n\n".join(current))
            current = [para]
            continue
        current.append(para)
        if _token_count("\n\n".join(current)) >= target:
            sections.append("\n\n".join(current))
            current = []
    if current:
        sections.append("\n\n".join(current))

    # Enforce size with overlap windows
    out: list[str] = []
    for section in sections:
        words = _WORD.findall(section)
        if len(words) <= target + 100:
            out.append(section)
            continue
        step = max(1, target - overlap)
        for start in range(0, len(words), step):
            window = words[start : start + target]
            if not window:
                break
            out.append(" ".join(window))
            if start + target >= len(words):
                break
    return out or [text]


def chunk_document(
    doc: ParsedDocument,
    *,
    target_tokens: int = 500,
    overlap_tokens: int = 80,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    for page in doc.pages:
        if page.is_table:
            chunks.append(
                Chunk(
                    chunk_index=idx,
                    text=page.text,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    is_table=True,
                    metadata={"section_heading": "table", "filename": doc.metadata.get("filename")},
                )
            )
            idx += 1
            continue

        for part in _split_prose(page.text, target=target_tokens, overlap=overlap_tokens):
            heading = part.splitlines()[0][:80] if part.splitlines() else ""
            chunks.append(
                Chunk(
                    chunk_index=idx,
                    text=part,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    is_table=False,
                    metadata={"section_heading": heading, "filename": doc.metadata.get("filename")},
                )
            )
            idx += 1
    return chunks
