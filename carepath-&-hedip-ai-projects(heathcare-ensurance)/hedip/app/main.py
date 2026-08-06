"""FastAPI Command Center (:8009)."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel, Field

from app.graph import build_graph_with_backends, make_initial_state
from app.state import Domain
from app.tools.cases import list_cases

UI_DIR = Path(__file__).resolve().parent / "ui"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_threads: dict[str, dict[str, Any]] = {}
_graph = None


def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph_with_backends()
    return _graph


@asynccontextmanager
async def lifespan(_app: FastAPI):
    os.environ.setdefault("HEDIP_MODEL", "fake")
    _get_graph()
    yield


class RunRequest(BaseModel):
    query: str
    domain: Domain | None = None
    case_id: str = ""
    user_id: str = "demo-user"
    role: str = "payer_reviewer"


class ApproveRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_body: str | None = None


def _has_interrupt(graph, config: dict) -> bool:
    snap = graph.get_state(config)
    return any(intr for task in snap.tasks for intr in task.interrupts)


def _interrupt_payload(graph, config: dict) -> dict[str, Any] | None:
    snap = graph.get_state(config)
    for task in snap.tasks:
        for intr in task.interrupts:
            val = getattr(intr, "value", None)
            if isinstance(val, dict):
                return val
    return None


def _run(thread_id: str, body: RunRequest) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = make_initial_state(
        thread_id=thread_id,
        query=body.query,
        domain=body.domain,
        case_id=body.case_id,
        user_id=body.user_id,
        role=body.role,
    )
    try:
        for _ in graph.stream(state, config, stream_mode="updates"):
            pass
        if _has_interrupt(graph, config):
            _threads[thread_id]["status"] = "pending_hitl"
            _threads[thread_id]["interrupt"] = _interrupt_payload(graph, config)
        else:
            _threads[thread_id]["status"] = "completed"
        _threads[thread_id]["values"] = dict(graph.get_state(config).values)
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)
        logger.exception("HEDIP run failed")


def _resume(thread_id: str, payload: dict) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        graph.invoke(Command(resume=payload), config)
        snap = graph.get_state(config)
        _threads[thread_id]["values"] = dict(snap.values)
        if _has_interrupt(graph, config):
            _threads[thread_id]["status"] = "pending_hitl"
            _threads[thread_id]["interrupt"] = _interrupt_payload(graph, config)
        else:
            _threads[thread_id]["status"] = "completed"
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)


app = FastAPI(title="HEDIP Command Center", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(UI_DIR / "console.html")


@app.get("/api/domains")
async def domains() -> list[dict[str, str]]:
    return [
        {"id": "prior_auth", "label": "Prior Authorization"},
        {"id": "claims", "label": "Claims Denial Prevention"},
        {"id": "clinical_cds", "label": "Clinical CDS"},
        {"id": "care_coord", "label": "Care Coordination"},
        {"id": "knowledge", "label": "Enterprise Knowledge"},
        {"id": "fraud", "label": "Fraud / W&A"},
        {"id": "pop_health", "label": "Population Health"},
        {"id": "rcm", "label": "Revenue Cycle"},
    ]


@app.get("/api/cases")
async def cases(domain: str | None = None) -> list[dict[str, Any]]:
    return list_cases(domain)


@app.post("/run")
async def run(body: RunRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "status": "running",
        "error": None,
        "domain": body.domain,
        "case_id": body.case_id,
        "values": {},
        "interrupt": None,
    }
    background_tasks.add_task(_run, thread_id, body)
    return {"thread_id": thread_id}


@app.get("/status/{thread_id}")
async def status(thread_id: str) -> dict[str, Any]:
    meta = _threads.get(thread_id)
    if not meta:
        raise HTTPException(404, "Unknown thread")
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        values = dict(graph.get_state(config).values or {})
    except Exception:
        values = dict(meta.get("values") or {})
    return {
        "thread_id": thread_id,
        "status": meta.get("status"),
        "error": meta.get("error"),
        "domain": values.get("domain") or meta.get("domain"),
        "case_id": values.get("case_id") or meta.get("case_id"),
        "step_log": values.get("step_log") or [],
        "draft": values.get("draft") or values.get("final_response"),
        "recommendation": values.get("recommendation"),
        "citations": values.get("citations") or [],
        "safety_score": values.get("safety_score"),
        "judges": values.get("judges"),
        "approval": values.get("approval"),
        "published": values.get("published"),
        "interrupt": meta.get("interrupt") or _interrupt_payload(graph, config),
    }


@app.post("/approve/{thread_id}")
async def approve(thread_id: str, body: ApproveRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    meta = _threads.get(thread_id)
    if not meta:
        raise HTTPException(404, "Unknown thread")
    if meta.get("status") != "pending_hitl":
        raise HTTPException(400, f"Not awaiting HITL ({meta.get('status')})")
    meta["status"] = "running"
    background_tasks.add_task(_resume, thread_id, {"action": body.action, "edited_body": body.edited_body})
    return {"thread_id": thread_id, "status": "resuming"}


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8009, reload=False)


if __name__ == "__main__":
    main()
