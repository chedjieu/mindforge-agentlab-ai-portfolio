"""Structure-aware chunking with parent/child and page provenance."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.ingestion.pdf_io import ParsedDocument

HEADING = re.compile(r"^(#{1,3}\s+|[A-Z][A-Z0-9 /&-]{8,}|Section\s+\d+|^\d+\.\s+[A-Z]).*")


@dataclass
class ChunkDraft:
    text: str
    page_number: int
    section: str
    parent_section: str


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s or len(s) > 120:
        return False
    if s.startswith("#"):
        return True
    if s.isupper() and len(s.split()) <= 12:
        return True
    return bool(HEADING.match(s))


def chunk_document(parsed: ParsedDocument, max_chars: int = 900) -> list[ChunkDraft]:
    chunks: list[ChunkDraft] = []
    section = "Preamble"
    parent = "Document"
    buf: list[str] = []
    page_for_buf = 1

    def flush() -> None:
        nonlocal buf
        text = "\n".join(buf).strip()
        if text:
            chunks.append(
                ChunkDraft(
                    text=text,
                    page_number=page_for_buf,
                    section=section,
                    parent_section=parent,
                )
            )
        buf = []

    for page in parsed.pages:
        page_for_buf = page.page_number
        for line in page.text.splitlines():
            if _is_heading(line):
                flush()
                parent = section
                section = line.strip().lstrip("#").strip()
                continue
            buf.append(line)
            if sum(len(x) for x in buf) >= max_chars:
                flush()
        flush()

    if not chunks and parsed.pages:
        for page in parsed.pages:
            if page.text.strip():
                chunks.append(
                    ChunkDraft(
                        text=page.text.strip(),
                        page_number=page.page_number,
                        section="Body",
                        parent_section="Document",
                    )
                )
    # Parent-child: emit a parent chunk per section (concat children, truncated).
    by_section: dict[str, list[ChunkDraft]] = {}
    for c in chunks:
        by_section.setdefault(c.section, []).append(c)
    parents: list[ChunkDraft] = []
    for sec, kids in by_section.items():
        joined = " ".join(k.text for k in kids)
        parents.append(
            ChunkDraft(
                text=joined[:1500],
                page_number=kids[0].page_number,
                section=f"PARENT::{sec}",
                parent_section=sec,
            )
        )
    return chunks + parents


def chunk_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]
