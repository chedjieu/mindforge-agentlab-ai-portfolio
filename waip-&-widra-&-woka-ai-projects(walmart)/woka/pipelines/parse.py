"""PDF parser — text + lightweight table detection via pypdf."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

from pipelines.classify import classify_pdf
from pipelines.models import ParsedDocument, ParsedPage

_TABLE_HINT = re.compile(
    r"(?i)(\|.*\|)|(\t.+\t)|(\b(table|capex|sku|qty|inventory|sla|%\b)\b.+\d)"
)


def _looks_like_table(text: str) -> bool:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    pipe_rows = sum(1 for ln in lines if ln.count("|") >= 2)
    tab_rows = sum(1 for ln in lines if ln.count("\t") >= 2)
    if pipe_rows >= 2 or tab_rows >= 2:
        return True
    return bool(_TABLE_HINT.search(text)) and len(lines) <= 12


def parse_pdf(path: Path) -> ParsedDocument:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF: {path}")

    classification = classify_pdf(path)
    reader = PdfReader(str(path))
    pages: list[ParsedPage] = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            # OCR hook placeholder for scanned pages (Phase 2 keeps text path)
            continue
        pages.append(
            ParsedPage(
                page_number=i,
                text=text,
                is_table=_looks_like_table(text),
            )
        )

    title = path.stem.replace("_", " ").strip() or path.name
    meta: dict = {
        "filename": path.name,
        "page_count": len(reader.pages),
        "classification": classification,
    }
    if reader.metadata:
        if reader.metadata.title:
            title = str(reader.metadata.title)
        if reader.metadata.author:
            meta["author"] = str(reader.metadata.author)

    if not pages:
        raise ValueError(f"No extractable text in {path.name} (strategy={classification['strategy']})")

    return ParsedDocument(
        path=str(path),
        title=title,
        pages=pages,
        metadata=meta,
        doc_class=str(classification["doc_class"]),
    )
