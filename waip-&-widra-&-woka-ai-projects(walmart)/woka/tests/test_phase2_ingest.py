"""Phase 2 ingestion tests."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["WOKA_MODEL"] = "fake"
os.environ["WOKA_EMBEDDINGS"] = "fake"

from pipelines.chunker import chunk_document
from pipelines.classify import classify_pdf
from pipelines.embed import embed_chunks
from pipelines.parse import parse_pdf

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample_docs"


def test_classify_and_parse() -> None:
    path = SAMPLE / "01_se_dc_contingency_sop.pdf"
    assert path.exists()
    info = classify_pdf(path)
    assert info["doc_class"] in {"text_pdf", "table_pdf", "form_pdf", "scanned_pdf"}
    doc = parse_pdf(path)
    assert doc.pages
    assert "contingency" in doc.title.lower() or "southeast" in doc.title.lower() or doc.pages[0].text


def test_chunk_metadata_enrichment() -> None:
    path = SAMPLE / "02_acme_vendor_contract.pdf"
    doc = parse_pdf(path)
    chunks = chunk_document(doc)
    assert chunks
    meta = chunks[0].metadata
    assert meta.get("department")
    assert meta.get("confidentiality")
    assert "filename" in meta


def test_embed_and_ingest_dir() -> None:
    from app.agents.document import run_ingestion
    from app.config import get_settings
    from app.llm import reset_llm_cache

    get_settings.cache_clear()
    reset_llm_cache()

    path = SAMPLE / "04_inventory_policy.pdf"
    doc = parse_pdf(path)
    chunks = chunk_document(doc)
    embedded = embed_chunks(chunks)
    assert all(c.embedding and len(c.embedding) == 64 for c in embedded)

    pdfs = sorted(SAMPLE.glob("*.pdf"))
    assert len(pdfs) >= 8
    result = run_ingestion(pdfs)
    results = result.get("results") or []
    ok = [r for r in results if r.get("status") == "complete"]
    failed = [r for r in results if r.get("status") == "failed"]
    assert len(ok) == len(pdfs), failed
    assert sum(int(r.get("chunk_count") or 0) for r in ok) >= len(pdfs)
    assert result.get("job_id")
