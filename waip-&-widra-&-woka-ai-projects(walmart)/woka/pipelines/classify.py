"""Lightweight document classification for parser strategy selection."""

from __future__ import annotations

import re
from pathlib import Path

from pypdf import PdfReader

_TABLE = re.compile(r"(?i)(\|.*\|)|(\b(table|sku|qty|inventory|sla)\b.+\d)")
_FORM = re.compile(r"(?i)\b(form|application|signature|checkbox)\b")


def classify_pdf(path: Path) -> dict[str, object]:
    """Inspect PDF and choose extraction strategy."""
    path = Path(path)
    reader = PdfReader(str(path))
    page_count = len(reader.pages)
    sample_texts: list[str] = []
    empty_pages = 0
    for page in reader.pages[: min(3, page_count)]:
        text = (page.extract_text() or "").strip()
        if not text:
            empty_pages += 1
        else:
            sample_texts.append(text)

    joined = "\n".join(sample_texts)
    scanned = page_count > 0 and empty_pages == min(3, page_count)
    has_tables = bool(_TABLE.search(joined))
    has_forms = bool(_FORM.search(joined))

    if scanned:
        strategy = "ocr"
        doc_class = "scanned_pdf"
    elif has_tables:
        strategy = "table_parser"
        doc_class = "table_pdf"
    elif has_forms:
        strategy = "form_extractor"
        doc_class = "form_pdf"
    else:
        strategy = "text_parser"
        doc_class = "text_pdf"

    return {
        "doc_class": doc_class,
        "strategy": strategy,
        "page_count": page_count,
        "has_tables": has_tables,
        "has_forms": has_forms,
        "scanned": scanned,
    }
