"""Semantic + table-aware chunker with WOKA metadata enrichment."""

from __future__ import annotations

import re
from pathlib import Path

from pipelines.models import Chunk, ParsedDocument

_HEADING = re.compile(r"^(?:[A-Z][A-Za-z0-9 /&\-]{2,60}|#{1,3}\s+.+)$")
_WORD = re.compile(r"\S+")
_SKU = re.compile(r"\b([A-Z]{2,}(?:-[A-Z0-9]+){1,3})\b")
_SUPPLIER = re.compile(r"\b(SUP-[A-Z0-9]+|Acme Logistics|GulfFresh Produce|Northern Goods Co)\b", re.I)
_REGION = re.compile(r"\b(SE|SC|MW|NE|NW|Southwest|Southeast|California|CA)\b")
_CONTRACT = re.compile(r"\b(C-[A-Z]+-\d{4})\b")


def _token_count(text: str) -> int:
    return len(_WORD.findall(text))


def _split_prose(text: str, target: int = 500, overlap: int = 80) -> list[str]:
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


def _infer_department(filename: str, title: str, text: str) -> str:
    blob = f"{filename} {title} {text[:400]}".lower()
    if any(k in blob for k in ("payroll", "hazardous", "return policy", "store ops")):
        return "Store Ops"
    if any(k in blob for k in ("fda", "recall", "compliance")):
        return "Compliance"
    if any(k in blob for k in ("dc", "supply", "inventory", "vendor", "shipment", "contingency")):
        return "Supply Chain"
    return "General"


def _enrich(text: str, filename: str, title: str, heading: str, doc: ParsedDocument) -> dict:
    skus = list({m.group(1) for m in _SKU.finditer(text)})[:8]
    suppliers = list({m.group(1) for m in _SUPPLIER.finditer(text)})[:5]
    regions = list({m.group(1).upper() if len(m.group(1)) <= 3 else m.group(1) for m in _REGION.finditer(text)})[:5]
    contracts = list({m.group(1) for m in _CONTRACT.finditer(text)})[:5]
    dept = _infer_department(filename, title, text)
    confidentiality = "confidential" if "confidential" in text.lower() else "internal"
    if "executive" in f"{filename} {title}".lower():
        confidentiality = "restricted"
    return {
        "filename": filename,
        "section_heading": heading,
        "department": dept,
        "bu": dept,
        "region": regions[0] if regions else "US",
        "country": "US",
        "sku": skus,
        "supplier": suppliers,
        "category": doc.doc_class,
        "confidentiality": confidentiality,
        "keywords": list({*skus, *contracts, *suppliers})[:12],
        "entity_ids": list({*skus, *contracts, *suppliers})[:12],
        "doc_class": doc.doc_class,
    }


def chunk_document(
    doc: ParsedDocument,
    *,
    target_tokens: int = 500,
    overlap_tokens: int = 80,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    idx = 0
    filename = str(doc.metadata.get("filename") or Path(doc.path).name)
    for page in doc.pages:
        if page.is_table:
            meta = _enrich(page.text, filename, doc.title, "table", doc)
            chunks.append(
                Chunk(
                    chunk_index=idx,
                    text=page.text,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    is_table=True,
                    metadata=meta,
                )
            )
            idx += 1
            continue

        for part in _split_prose(page.text, target=target_tokens, overlap=overlap_tokens):
            heading = part.splitlines()[0][:80] if part.splitlines() else ""
            meta = _enrich(part, filename, doc.title, heading, doc)
            chunks.append(
                Chunk(
                    chunk_index=idx,
                    text=part,
                    page_start=page.page_number,
                    page_end=page.page_number,
                    is_table=False,
                    metadata=meta,
                )
            )
            idx += 1
    return chunks
