"""FastAPI entrypoint for the agentic RAG chatbot."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from src.agent.graph import run_agent
from src.config import get_settings
from src.ingest import run_ingest
from src.rag.vectorstore import collection_count

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic RAG Chatbot API",
    description="LangChain agent + ChromaDB knowledge assistant for Lilian Weng posts.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str = "default"


class Source(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source] = []
    steps: list[dict[str, Any]] = []
    session_id: str
    error: str | None = None


class IngestResponse(BaseModel):
    status: str
    result: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    knowledge_base_documents: int
    chat_model: str
    embedding_model: str


@app.get("/")
def root() -> RedirectResponse:
    """Browser-friendly entry: send / to interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        knowledge_base_documents=collection_count(settings),
        chat_model=settings.openai_chat_model,
        embedding_model=settings.openai_embedding_model,
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the API server.",
        )

    try:
        result = run_agent(request.message.strip(), settings=settings)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat failed")
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    _append_local_log(
        session_id=request.session_id,
        query=request.message,
        answer=result.get("answer", ""),
        sources=result.get("sources") or [],
    )

    return ChatResponse(
        answer=result.get("answer", ""),
        sources=[Source(**s) for s in (result.get("sources") or [])],
        steps=result.get("steps") or [],
        session_id=request.session_id,
        error=result.get("error"),
    )


@app.post("/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=500,
            detail="OPENAI_API_KEY is not configured on the API server.",
        )
    try:
        result = run_ingest(settings)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingest failed")
        raise HTTPException(status_code=500, detail=f"Ingest error: {exc}") from exc
    return IngestResponse(status="ok", result=result)


def _append_local_log(
    *,
    session_id: str,
    query: str,
    answer: str,
    sources: list[dict[str, str]],
) -> None:
    """Best-effort JSONL log for local demos (n8n also logs separately)."""
    settings = get_settings()
    logs_dir = Path(settings.logs_dir)
    try:
        logs_dir.mkdir(parents=True, exist_ok=True)
        path = logs_dir / "chat_log.jsonl"
        import json

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "query": query,
            "answer": answer,
            "sources": sources,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        logger.warning("Failed to write local chat log", exc_info=True)


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
