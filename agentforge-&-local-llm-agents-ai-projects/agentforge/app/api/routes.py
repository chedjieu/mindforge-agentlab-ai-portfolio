from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app import __version__
from app.agents.graph import run_agent, stream_agent
from app.api.schemas import (
    ChatRequest,
    ChatResponse,
    EvalRequest,
    EvalResponse,
    HealthResponse,
    IngestRequest,
    IngestResponse,
)
from app.config import get_settings
from app.eval.runners import run_evaluation
from app.guardrails.input_filter import validate_user_message
from app.rag.ingest import ingest_pdf
from app.rag.store import collection_count

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    count = collection_count(settings.rag_collection, settings)
    return HealthResponse(
        status="ok",
        version=__version__,
        ollama_host=settings.ollama_host,
        chroma_ready=True,
        documents_indexed=count,
    )


@router.post("/ingest", response_model=IngestResponse)
def ingest(body: IngestRequest) -> IngestResponse:
    try:
        result = ingest_pdf(body.pdf_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return IngestResponse(**result)


@router.post("/chat")
async def chat(body: ChatRequest):
    guard = validate_user_message(body.message)
    if not guard.allowed:
        raise HTTPException(status_code=400, detail=guard.reason)

    if body.stream:

        async def event_generator() -> AsyncIterator[dict]:
            for item in stream_agent(body.message, thread_id=body.thread_id):
                yield {
                    "event": item.get("type", "message"),
                    "data": json.dumps(item, default=str),
                }

        return EventSourceResponse(event_generator())

    result = run_agent(body.message, thread_id=body.thread_id)
    return ChatResponse(**result)



@router.post("/eval", response_model=EvalResponse)
def evaluate(body: EvalRequest) -> EvalResponse:
    results = run_evaluation(run_sample=body.run_sample)
    return EvalResponse(status="ok", results=results)
