"""FastAPI Document Console — WIDRA BFF."""

from __future__ import annotations

import json
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import ping as db_ping
from app.llm import get_chat_model

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_PDFS = ROOT / "data" / "sample_pdfs"

app = FastAPI(title="WIDRA Document Console", version="0.1.0")


class QueryRequest(BaseModel):
    query: str
    user_id: str = "user-001"
    role: str = "associate"


class Citation(BaseModel):
    doc_id: str
    title: str
    page: int
    snippet: str


class QueryResponse(BaseModel):
    status: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    model: str
    note: str = ""


class IngestRequest(BaseModel):
    dir: str | None = None


@app.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    sample_count = len(list(SAMPLE_PDFS.glob("*.pdf"))) if SAMPLE_PDFS.exists() else 0
    local_docs = ROOT / "data" / "local_store" / "metadata" / "documents.jsonl"
    indexed = 0
    if local_docs.exists():
        indexed = sum(1 for line in local_docs.read_text(encoding="utf-8").splitlines() if line.strip())
    return {
        "status": "ok",
        "service": "widra",
        "phase": 2,
        "model": settings.widra_model,
        "postgres": db_ping(),
        "sample_pdfs": sample_count,
        "local_indexed_docs": indexed,
    }


@app.post("/ingest")
def ingest(body: IngestRequest | None = None) -> dict[str, object]:
    """Ingest sample PDFs (or paths provided) via the Ingestion Agent."""
    from app.agents.ingestion import run_ingestion

    payload = body or IngestRequest()
    directory = Path(payload.dir) if payload.dir else SAMPLE_PDFS
    pdfs = sorted(directory.glob("*.pdf")) if directory.is_dir() else []
    if not pdfs:
        return {"status": "error", "message": f"No PDFs in {directory}"}
    result = run_ingestion(pdfs)
    results = result.get("results") or []
    ok = sum(1 for r in results if r.get("status") == "complete")
    return {
        "status": "complete",
        "job_id": result.get("job_id"),
        "docs_ok": ok,
        "docs_total": len(results),
        "chunks": sum(int(r.get("chunk_count") or 0) for r in results),
        "results": results,
    }


@app.post("/query", response_model=QueryResponse)
def query(body: QueryRequest) -> QueryResponse:
    """Stub query endpoint — returns fake grounded answer until Phase 4."""
    settings = get_settings()
    llm = get_chat_model()
    raw = llm.invoke(
        f"User ({body.role}): {body.query}\n"
        f"Retrieve relevant Walmart document chunks and answer with citations."
    )
    payload = json.loads(str(raw.content))
    citations = [Citation(**c) for c in payload.get("citations", [])]
    return QueryResponse(
        status="stub",
        answer=payload.get("answer", ""),
        citations=citations,
        model=settings.widra_model,
        note="Phase 1 stub — retrieval pipeline wired in Phase 3.",
    )


@app.get("/sample-docs")
def sample_docs() -> list[dict[str, str]]:
    if not SAMPLE_PDFS.exists():
        return []
    return [{"filename": p.name, "size_bytes": str(p.stat().st_size)} for p in sorted(SAMPLE_PDFS.glob("*.pdf"))]


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8005, reload=False)


if __name__ == "__main__":
    main()
