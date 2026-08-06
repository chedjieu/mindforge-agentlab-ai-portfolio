"""FastAPI entrypoint for the EGKP approval console (:8002)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel

from app.graph import SAMPLE_QUERY, build_graph, make_initial_state

UI_DIR = Path(__file__).resolve().parent / "ui"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_threads: dict[str, dict[str, str | None]] = {}
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _get_graph()
    yield


class AskRequest(BaseModel):
    query: str
    user_id: str = "demo-user"
    role: str = "engineer"
    domain: str | None = None


class ApproveRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_body: str | None = None


def _has_pending_interrupt(graph, config: dict) -> bool:
    snap = graph.get_state(config)
    return any(intr for task in snap.tasks for intr in task.interrupts)


def _run_until_pause(
    thread_id: str,
    query: str,
    user_id: str,
    role: str,
    domain: str | None,
) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = make_initial_state(
        thread_id=thread_id,
        query=query,
        user_id=user_id,
        role=role,
    )
    if domain:
        # Optional hint — intent_router still runs and may override.
        state["domain"] = domain  # type: ignore[typeddict-item]
    try:
        for _ in graph.stream(state, config, stream_mode="updates"):
            pass
        if _has_pending_interrupt(graph, config):
            _threads[thread_id]["status"] = "pending_hitl"
        else:
            _threads[thread_id]["status"] = "completed"
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)
        logger.exception("Query processing failed for %s", thread_id)


def _resume(thread_id: str, payload: dict) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        graph.invoke(Command(resume=payload), config)
        _threads[thread_id]["status"] = "completed"
        _threads[thread_id]["error"] = None
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)
        logger.exception("Resume failed for %s", thread_id)


app = FastAPI(title="Panasonic EGKP", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(UI_DIR / "approval.html")


@app.post("/ask")
async def ask(body: AskRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "domain": body.domain or "",
        "status": "running",
        "error": None,
        "query": body.query[:200],
    }
    background_tasks.add_task(
        _run_until_pause,
        thread_id,
        body.query,
        body.user_id,
        body.role,
        body.domain,
    )
    return {"thread_id": thread_id}


@app.post("/ask/demo")
async def ask_demo(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Manufacturing PN-4421 torque demo query."""
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "domain": "manufacturing",
        "status": "running",
        "error": None,
        "query": SAMPLE_QUERY[:200],
    }
    background_tasks.add_task(
        _run_until_pause,
        thread_id,
        SAMPLE_QUERY,
        "demo-user",
        "engineer",
        "manufacturing",
    )
    return {"thread_id": thread_id}


@app.post("/ask/demo-hr")
async def ask_demo_hr(background_tasks: BackgroundTasks) -> dict[str, str]:
    """HR PTO demo — forces HITL."""
    query = "What is PTO accrual for full-time US employees?"
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "domain": "hr",
        "status": "running",
        "error": None,
        "query": query,
    }
    background_tasks.add_task(
        _run_until_pause,
        thread_id,
        query,
        "hr-user",
        "employee",
        "hr",
    )
    return {"thread_id": thread_id}


@app.get("/threads")
async def list_threads() -> list[dict]:
    return [{"thread_id": thread_id, **meta} for thread_id, meta in _threads.items()]


@app.get("/pending")
async def pending() -> list[dict]:
    graph = _get_graph()
    pending_items: list[dict] = []
    for thread_id in list(_threads):
        config = {"configurable": {"thread_id": thread_id}}
        snap = graph.get_state(config)
        for task in snap.tasks:
            for intr in task.interrupts:
                pending_items.append({"thread_id": thread_id, "payload": intr.value})
    return pending_items


@app.post("/approve/{thread_id}")
async def approve(
    thread_id: str, body: ApproveRequest, background_tasks: BackgroundTasks
) -> dict:
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    payload = {"action": body.action, "edited_body": body.edited_body}
    _threads[thread_id]["status"] = "resuming"
    background_tasks.add_task(_resume, thread_id, payload)
    return {"thread_id": thread_id, "action": body.action, "status": "resumed"}


def main() -> None:
    """Run with: uv run python -m app.main"""
    import uvicorn

    from app.llm import DEFAULT_MODEL
    from app._fake_llm import is_fake_chat_model

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8002"))
    model = os.getenv("EGKP_MODEL", DEFAULT_MODEL)
    mode = "offline fake" if is_fake_chat_model(model) else "real cloud"
    print("\n  Panasonic EGKP — Approval Console")
    print(f"  Model: {model} ({mode})")
    print(f"  Open: http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
