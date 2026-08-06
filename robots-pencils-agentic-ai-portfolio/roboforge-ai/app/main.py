"""FastAPI Forge Console on :8003."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel

from app.graph import SAMPLE_CLIENT, SAMPLE_PACK, build_graph, make_initial_state

UI_DIR = Path(__file__).resolve().parent / "ui"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
_threads: dict[str, dict] = {}
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


class IngestRequest(BaseModel):
    pack: dict
    client_id: str


class ApproveRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_body: str | None = None


def _has_interrupt(graph, config: dict) -> bool:
    snap = graph.get_state(config)
    return any(intr for task in snap.tasks for intr in task.interrupts)


def _run(thread_id: str, pack: dict, client_id: str) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = make_initial_state(str(pack.get("id") or thread_id), pack, client_id)
    try:
        for _ in graph.stream(state, config, stream_mode="updates"):
            pass
        _threads[thread_id]["status"] = (
            "pending_hitl" if _has_interrupt(graph, config) else "completed"
        )
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)
        logger.exception("Forge run failed")


def _resume(thread_id: str, payload: dict) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        graph.invoke(Command(resume=payload), config)
        _threads[thread_id]["status"] = "completed"
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)


app = FastAPI(title="RoboForge AI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(UI_DIR / "forge.html")


@app.post("/forge")
async def forge(body: IngestRequest, background_tasks: BackgroundTasks) -> dict:
    thread_id = str(uuid4())
    _threads[thread_id] = {"client_id": body.client_id, "status": "running", "error": None}
    background_tasks.add_task(_run, thread_id, body.pack, body.client_id)
    return {"thread_id": thread_id}


@app.post("/forge/demo")
async def forge_demo(background_tasks: BackgroundTasks) -> dict:
    thread_id = str(uuid4())
    _threads[thread_id] = {"client_id": SAMPLE_CLIENT, "status": "running", "error": None}
    background_tasks.add_task(_run, thread_id, SAMPLE_PACK, SAMPLE_CLIENT)
    return {"thread_id": thread_id}


@app.get("/threads")
async def threads() -> list[dict]:
    return [{"thread_id": t, **m} for t, m in _threads.items()]


@app.get("/pending")
async def pending() -> list[dict]:
    graph = _get_graph()
    items = []
    for thread_id in list(_threads):
        config = {"configurable": {"thread_id": thread_id}}
        snap = graph.get_state(config)
        for task in snap.tasks:
            for intr in task.interrupts:
                items.append({"thread_id": thread_id, "payload": intr.value})
    return items


@app.post("/approve/{thread_id}")
async def approve(thread_id: str, body: ApproveRequest, background_tasks: BackgroundTasks) -> dict:
    if thread_id not in _threads:
        raise HTTPException(404, "Unknown thread_id")
    _threads[thread_id]["status"] = "resuming"
    background_tasks.add_task(
        _resume, thread_id, {"action": body.action, "edited_body": body.edited_body}
    )
    return {"thread_id": thread_id, "status": "resumed"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8003, reload=False)
