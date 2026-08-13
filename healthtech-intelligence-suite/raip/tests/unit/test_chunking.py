from app.ingestion.chunking import chunk_document
from app.ingestion.pdf_io import ParsedDocument, ParsedPage, sha256_bytes


def test_structure_aware_keeps_page() -> None:
    parsed = ParsedDocument(
        pages=[
            ParsedPage(1, "PURPOSE\nThis is the purpose paragraph.\n"),
            ParsedPage(2, "CLINICAL MANAGEMENT RECOMMENDATIONS\nMetformin is first-line therapy unless contraindicated.\n"),
        ],
        ocr_required=False,
        checksum="abc",
        mime="text/plain",
    )
    chunks = chunk_document(parsed)
    assert any(c.page_number == 2 and "Metformin" in c.text for c in chunks)
    assert any(c.section.startswith("PARENT::") for c in chunks)


def test_hash_stable() -> None:
    assert sha256_bytes(b"a") == sha256_bytes(b"a")
    assert sha256_bytes(b"a") != sha256_bytes(b"b")
