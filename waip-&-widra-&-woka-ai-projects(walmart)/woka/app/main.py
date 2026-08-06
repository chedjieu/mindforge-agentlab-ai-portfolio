"""FastAPI Knowledge Console — WOKA BFF."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.db import ping as db_ping
from app.observability.langsmith import langsmith_meta

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOCS = ROOT / "data" / "sample_docs"
UI = Path(__file__).resolve().parent / "ui"

app = FastAPI(title="WOKA Knowledge Console", version="0.1.0")


class ChatRequest(BaseModel):
    query: str
    user_id: str = "user-sc-001"
    role: str = "analyst"
    department: str = "Supply Chain"
    region: str = "SE"


class Citation(BaseModel):
    doc_id: str
    title: str
    page: int = 0
    section: str = ""
    snippet: str = ""
    confidence: float = 0.0
    source_type: str = "internal"


class ChatResponse(BaseModel):
    status: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    agents_used: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    model: str
    note: str = ""
    step_log: list[str] = Field(default_factory=list)
    compliance: dict[str, Any] = Field(default_factory=dict)
    judges: dict[str, Any] = Field(default_factory=dict)
    audit_id: str = ""


def _citations_from_state(state: dict[str, Any]) -> list[Citation]:
    out: list[Citation] = []
    for c in state.get("citations") or []:
        try:
            out.append(
                Citation(
                    doc_id=str(c.get("doc_id") or "unknown"),
                    title=str(c.get("title") or ""),
                    page=int(c.get("page") or 0),
                    section=str(c.get("section") or ""),
                    snippet=str(c.get("snippet") or ""),
                    confidence=float(c.get("confidence") or 0.0),
                    source_type=str(c.get("source_type") or "internal"),
                )
            )
        except Exception:  # noqa: BLE001
            continue
    return out


def _chat_response(state: dict[str, Any]) -> ChatResponse:
    settings = get_settings()
    blocked = bool(state.get("blocked"))
    return ChatResponse(
        status="blocked" if blocked else "ok",
        answer=str(state.get("final_response") or state.get("answer") or ""),
        citations=_citations_from_state(state),
        agents_used=list(state.get("agents_used") or []),
        confidence=float(state.get("confidence") or 0.0),
        model=settings.woka_model,
        note="Phase 5 UC-1 path with judges + audit.",
        step_log=list(state.get("step_log") or []),
        compliance=dict(state.get("compliance") or {}),
        judges=dict(state.get("judges") or {}),
        audit_id=str(state.get("audit_id") or ""),
    )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(UI / "console.html")


@app.get("/health")
def health() -> dict[str, object]:
    settings = get_settings()
    sample_count = len(list(SAMPLE_DOCS.glob("*.pdf"))) if SAMPLE_DOCS.exists() else 0
    indexed = 0
    if db_ping():
        try:
            from app.db import get_connection

            with get_connection() as conn:
                indexed = conn.execute(
                    "SELECT count(*) FROM documents WHERE parse_status = %s",
                    ("parsed",),
                ).fetchone()[0]
        except Exception:  # noqa: BLE001
            indexed = 0
    return {
        "status": "ok",
        "service": "woka",
        "phase": 6,
        "model": settings.woka_model,
        "postgres": db_ping(),
        "sample_docs": sample_count,
        "indexed_docs": indexed,
        "langsmith": langsmith_meta(),
        "backends": {
            "vector": settings.woka_vector_backend,
            "s3_mode": settings.woka_s3_mode,
            "pinecone_configured": bool(settings.pinecone_api_key and settings.pinecone_index_host),
        },
        "deploy": {
            "agentcore": "deploy/agentcore/entrypoint.py",
            "vertex": "deploy/vertex_engine/entrypoint.py",
        },
    }


class IngestRequest(BaseModel):
    dir: str | None = None


class BatchIngestRequest(BaseModel):
    dir: str | None = None
    workers: int = 4


@app.post("/ingest")
def ingest(body: IngestRequest | None = None) -> dict[str, object]:
    """Ingest sample (or provided) PDFs via the Document Agent."""
    from app.agents.document import run_ingestion
    from app.llm import reset_llm_cache

    if os.getenv("WOKA_INGEST_CLOUD", "").lower() not in {"1", "true", "yes"}:
        os.environ["WOKA_EMBEDDINGS"] = "fake"
        reset_llm_cache()

    payload = body or IngestRequest()
    directory = Path(payload.dir) if payload.dir else SAMPLE_DOCS
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


@app.post("/ingest/batch")
def ingest_batch(body: BatchIngestRequest | None = None) -> dict[str, object]:
    """Concurrent batch ingest for scale demos."""
    from pipelines.batch_ingest import collect_pdfs, run_batch

    if os.getenv("WOKA_INGEST_CLOUD", "").lower() not in {"1", "true", "yes"}:
        os.environ["WOKA_EMBEDDINGS"] = "fake"

    payload = body or BatchIngestRequest()
    directory = Path(payload.dir) if payload.dir else SAMPLE_DOCS
    pdfs = collect_pdfs(dirs=[directory])
    if not pdfs:
        return {"status": "error", "message": f"No PDFs in {directory}"}
    return run_batch(pdfs, workers=payload.workers)


@app.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    """UC-1 multi-agent orchestrator (firewall → parallel workers → compliance)."""
    from app.graph import run_uc1

    state = run_uc1(
        body.query,
        user_id=body.user_id,
        role=body.role,
        department=body.department,
        region=body.region,
    )
    return _chat_response(state)


@app.post("/chat/stream")
def chat_stream(body: ChatRequest) -> StreamingResponse:
    """SSE stream of LangGraph node updates, ending with a final ChatResponse payload."""

    def event_gen() -> Iterator[str]:
        from app.graph import get_graph

        graph = get_graph()
        config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        initial = {
            "query": body.query,
            "user_id": body.user_id,
            "role": body.role,
            "department": body.department,
            "region": body.region,
            "step_log": [],
            "worker_results": {},
        }
        for event in graph.stream(initial, config=config, stream_mode="updates"):
            for node, update in event.items():
                if isinstance(update, dict):
                    payload = {
                        "type": "step",
                        "node": node,
                        "keys": sorted(update.keys()),
                        "step_log": update.get("step_log") or [],
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

        snap = graph.get_state(config)
        state = dict(snap.values or {})
        resp = _chat_response(state)
        yield f"data: {json.dumps({'type': 'final', **resp.model_dump()})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@app.get("/search")
def search(
    q: str = "",
    limit: int = 5,
    user_id: str = "user-001",
    role: str = "analyst",
    department: str = "Supply Chain",
    region: str = "SE",
) -> dict[str, object]:
    """Hybrid search with Security Agent ACL pre-filter + GraphRAG hops."""
    from app.agents.retrieval import run_retrieval_agent
    from app.agents.security import run_security_agent, scope_from_request
    from app.llm import reset_llm_cache

    os.environ.setdefault("WOKA_EMBEDDINGS", os.getenv("WOKA_EMBEDDINGS", "fake"))
    if os.getenv("WOKA_EMBEDDINGS", "fake") == "fake":
        reset_llm_cache()

    sec = run_security_agent(
        user_id=user_id,
        role=role,
        department=department,
        region=region,
    )
    scope = scope_from_request(
        user_id=user_id,
        role=role,
        department=department,
        region=region,
    )
    retrieval = run_retrieval_agent(q, scope, top_k=limit)
    return {
        "status": "ok",
        "query": q,
        "limit": limit,
        "security": sec,
        "results": retrieval.get("chunks") or [],
        "graph_facts": retrieval.get("graph_facts") or [],
        "chunk_count": retrieval.get("chunk_count", 0),
        "graph_count": retrieval.get("graph_count", 0),
    }


@app.get("/documents")
def documents() -> list[dict[str, str]]:
    if not SAMPLE_DOCS.exists():
        return []
    return [{"filename": p.name, "size_bytes": str(p.stat().st_size)} for p in sorted(SAMPLE_DOCS.glob("*.pdf"))]


class EvaluateRequest(BaseModel):
    query: str | None = None
    answer: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    run_uc1: bool = False
    role: str = "analyst"
    department: str = "Supply Chain"
    region: str = "SE"
    user_id: str = "user-eval-001"
    suite: bool = False


@app.post("/evaluate")
def evaluate(body: EvaluateRequest) -> dict[str, Any]:
    """Run LLM-as-judge / heuristic gates, optional full UC-1, or full Phase 5 suite."""
    from app.observability.audit import write_audit
    from evals.judges import evaluate_answer

    if body.suite:
        from evals.run_all import run_all

        result = run_all()
        write_audit(
            user_id=body.user_id,
            action="evaluate_suite",
            query_text="suite",
            details={"pass": result.get("pass")},
        )
        return {"status": "ok", **result}

    if body.run_uc1 or (body.query and not body.answer):
        from app.graph import run_uc1

        q = body.query or (
            "Hurricane closed DCs in the Southeast. Which suppliers are affected "
            "and what inventory exists within 300 miles?"
        )
        state = run_uc1(
            q,
            user_id=body.user_id,
            role=body.role,
            department=body.department,
            region=body.region,
        )
        eval_result = evaluate_answer(
            query=q,
            answer=str(state.get("final_response") or state.get("answer") or ""),
            citations=list(state.get("citations") or []),
            sql=state.get("sql"),
            blocked=bool(state.get("blocked")),
        )
        write_audit(
            user_id=body.user_id,
            action="evaluate",
            query_text=q,
            details={"pass": eval_result.get("pass"), "audit_id": state.get("audit_id")},
        )
        return {
            "status": "ok",
            "pass": eval_result.get("pass"),
            "eval": eval_result,
            "answer": state.get("final_response"),
            "citations": state.get("citations"),
            "agents_used": state.get("agents_used"),
            "judges_from_graph": state.get("judges"),
        }

    eval_result = evaluate_answer(
        query=body.query or "",
        answer=body.answer or "",
        citations=list(body.citations or []),
    )
    write_audit(
        user_id=body.user_id,
        action="evaluate",
        query_text=body.query,
        details={"pass": eval_result.get("pass")},
    )
    return {"status": "ok", "pass": eval_result.get("pass"), "eval": eval_result}


class FeedbackRequest(BaseModel):
    query: str = ""
    answer: str = ""
    rating: int = Field(ge=1, le=5, default=5)
    comment: str = ""
    user_id: str = "user-feedback-001"
    audit_id: str = ""


@app.post("/feedback")
def feedback(body: FeedbackRequest) -> dict[str, Any]:
    from app.observability.audit import write_audit

    record = write_audit(
        user_id=body.user_id,
        action="feedback",
        query_text=body.query,
        details={
            "rating": body.rating,
            "comment": body.comment,
            "answer_preview": (body.answer or "")[:300],
            "related_audit_id": body.audit_id,
        },
    )
    return {"status": "ok", "feedback_id": record["audit_id"], "rating": body.rating}


@app.get("/audit")
def audit(limit: int = 50, action: str | None = None) -> dict[str, Any]:
    from app.observability.audit import list_audits

    items = list_audits(limit=limit, action=action)
    return {"status": "ok", "count": len(items), "items": items}


def main() -> None:
    import uvicorn

    from app.observability.langsmith import configure_langsmith

    configure_langsmith()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8006, reload=False)


if __name__ == "__main__":
    main()