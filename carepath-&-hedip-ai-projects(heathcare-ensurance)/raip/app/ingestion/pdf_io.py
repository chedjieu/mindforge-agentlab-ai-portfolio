"""Minimal PDF write/read with page-level provenance. OCR is detected, not faked."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedPage:
    page_number: int
    text: str


@dataclass
class ParsedDocument:
    pages: list[ParsedPage]
    ocr_required: bool
    checksum: str
    mime: str
    metadata: dict[str, str] = field(default_factory=dict)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_simple_pdf(path: Path, title: str, pages: list[str]) -> None:
    """Write a Helvetica PDF with one page object per source page."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = max(1, len(pages))
    font_id = 3 + 2 * n
    objs: dict[int, bytes] = {}

    def put(num: int, body: bytes) -> None:
        objs[num] = f"{num} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"

    kids = " ".join(f"{3 + i} 0 R" for i in range(n))
    put(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    put(2, f"<< /Type /Pages /Count {n} /Kids [{kids}] >>".encode("latin-1"))
    for i, text in enumerate(pages or [title]):
        page_id = 3 + i
        content_id = 3 + n + i
        escaped_lines = []
        for line in text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").split("\n")[:42]:
            escaped_lines.append(line[:110])
        stream = "\n".join(
            f"BT /F1 11 Tf 48 {740 - 16 * li} Td ({line}) Tj ET" for li, line in enumerate(escaped_lines)
        ).encode("latin-1", "replace")
        put(
            page_id,
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>"
            ).encode("latin-1"),
        )
        put(content_id, f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream")
    put(font_id, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    order = sorted(objs)
    parts = [header]
    offsets = {0: 0}
    running = len(header)
    for num in order:
        offsets[num] = running
        parts.append(objs[num])
        running += len(objs[num])
    xref = [f"xref\n0 {max(order) + 1}\n0000000000 65535 f \n".encode("latin-1")]
    for num in range(1, max(order) + 1):
        off = offsets.get(num, 0)
        xref.append(f"{off:010d} 00000 n \n".encode("latin-1"))
    trailer = f"trailer\n<< /Size {max(order) + 1} /Root 1 0 R >>\nstartxref\n{running}\n%%EOF\n".encode(
        "latin-1"
    )
    path.write_bytes(b"".join(parts + xref) + trailer)
    _ = title


def parse_bytes(filename: str, data: bytes) -> ParsedDocument:
    checksum = sha256_bytes(data)
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        text = data.decode("utf-8", errors="replace")
        raw_pages = re.split(r"\n\s*===PAGE\s+\d+\s*===\s*\n|\f", text)
        pages = [
            ParsedPage(page_number=i + 1, text=p.strip())
            for i, p in enumerate(raw_pages)
            if p.strip()
        ]
        if not pages:
            pages = [ParsedPage(1, text)]
        return ParsedDocument(pages=pages, ocr_required=False, checksum=checksum, mime="text/plain")

    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    pdf_pages: list[ParsedPage] = []
    empty = 0
    for i, page in enumerate(reader.pages, start=1):
        extracted = (page.extract_text() or "").strip()
        if not extracted:
            empty += 1
        pdf_pages.append(ParsedPage(page_number=i, text=extracted))
    ocr_required = bool(pdf_pages) and empty == len(pdf_pages)
    meta = {}
    if reader.metadata:
        meta["title"] = str(reader.metadata.title or "")
    return ParsedDocument(
        pages=pdf_pages,
        ocr_required=ocr_required,
        checksum=checksum,
        mime="application/pdf",
        metadata=meta,
    )
