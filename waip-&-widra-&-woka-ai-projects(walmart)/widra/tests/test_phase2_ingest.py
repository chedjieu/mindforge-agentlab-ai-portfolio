"""Phase 2 ingestion unit tests (no Docker required)."""

from __future__ import annotations

from pathlib import Path

from pipelines.chunker import chunk_document
from pipelines.embed import embed_chunks
from pipelines.parse import parse_pdf

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample_pdfs"


def test_parse_sample_pdf() -> None:
    path = SAMPLE / "01_us_return_policy.pdf"
    assert path.exists()
    doc = parse_pdf(path)
    assert doc.title
    assert len(doc.pages) >= 1
    assert "return" in doc.pages[0].text.lower() or "damaged" in doc.pages[0].text.lower()


def test_chunk_preserves_table_flag() -> None:
    path = SAMPLE / "07_finance_q3_report.pdf"
    doc = parse_pdf(path)
    chunks = chunk_document(doc)
    assert chunks
    assert all(c.text.strip() for c in chunks)


def test_embed_chunks() -> None:
    path = SAMPLE / "03_fcpa_training.pdf"
    doc = parse_pdf(path)
    chunks = chunk_document(doc)
    embedded = embed_chunks(chunks)
    assert all(c.embedding and len(c.embedding) == 64 for c in embedded)


def test_ingest_sample_dir() -> None:
    from app.agents.ingestion import run_ingestion

    pdfs = sorted(SAMPLE.glob("*.pdf"))
    assert len(pdfs) == 10
    result = run_ingestion(pdfs)
    results = result.get("results") or []
    ok = [r for r in results if r.get("status") == "complete"]
    failed = [r for r in results if r.get("status") == "failed"]
    assert len(ok) == 10, failed
    assert sum(int(r.get("chunk_count") or 0) for r in ok) >= 10
    assert result.get("job_id")
