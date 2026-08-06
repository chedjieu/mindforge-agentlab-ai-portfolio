"""FastAPI entrypoint for the CarePath clinician console (:8007)."""

from __future__ import annotations

import json
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

from app.graph import SAMPLE_QUERY, build_graph_with_backends, make_initial_state

UI_DIR = Path(__file__).resolve().parent / "ui"
PATIENTS_DIR = Path(__file__).resolve().parents[1] / "data" / "patients"

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
    os.environ.setdefault("CAREPATH_MODEL", "fake")
    _get_graph()
    yield


class PlanRequest(BaseModel):
    patient_id: str = "P001"
    clinician_id: str = "demo-clinician"
    query: str = SAMPLE_QUERY
    patient_preferences: dict[str, Any] = Field(default_factory=dict)


class ApproveRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_body: str | None = None


def _has_pending_interrupt(graph, config: dict) -> bool:
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


def _run_until_pause(
    thread_id: str,
    patient_id: str,
    clinician_id: str,
    query: str,
    preferences: dict[str, Any],
) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    # Load file preferences if caller didn't supply
    if not preferences:
        pref_path = PATIENTS_DIR / patient_id / "preferences.json"
        if pref_path.exists():
            preferences = json.loads(pref_path.read_text(encoding="utf-8"))
    state = make_initial_state(
        thread_id=thread_id,
        patient_id=patient_id,
        clinician_id=clinician_id,
        query=query,
        patient_preferences=preferences,
    )
    try:
        for _ in graph.stream(state, config, stream_mode="updates"):
            pass
        if _has_pending_interrupt(graph, config):
            _threads[thread_id]["status"] = "pending_hitl"
            _threads[thread_id]["interrupt"] = _interrupt_payload(graph, config)
        else:
            _threads[thread_id]["status"] = "completed"
        snap = graph.get_state(config)
        _threads[thread_id]["values"] = dict(snap.values)
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)
        logger.exception("Plan generation failed for %s", thread_id)


def _resume(thread_id: str, payload: dict) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        graph.invoke(Command(resume=payload), config)
        snap = graph.get_state(config)
        _threads[thread_id]["values"] = dict(snap.values)
        if _has_pending_interrupt(graph, config):
            _threads[thread_id]["status"] = "pending_hitl"
            _threads[thread_id]["interrupt"] = _interrupt_payload(graph, config)
        else:
            _threads[thread_id]["status"] = "completed"
            _threads[thread_id]["error"] = None
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)
        logger.exception("Resume failed for %s", thread_id)


app = FastAPI(title="CarePath AI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(UI_DIR / "console.html")


@app.get("/api/patients")
async def list_patients() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not PATIENTS_DIR.exists():
        return out
    for folder in sorted(PATIENTS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        ehr = folder / "ehr_bundle.json"
        prefs = folder / "preferences.json"
        item: dict[str, Any] = {"patient_id": folder.name}
        if ehr.exists():
            data = json.loads(ehr.read_text(encoding="utf-8"))
            item["display_name"] = data.get("display_name") or folder.name
            item["summary"] = data.get("summary") or ""
            item["conditions"] = data.get("conditions") or []
        if prefs.exists():
            item["preferences"] = json.loads(prefs.read_text(encoding="utf-8"))
        out.append(item)
    return out


@app.post("/plan")
async def create_plan(body: PlanRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "patient_id": body.patient_id,
        "status": "running",
        "error": None,
        "query": body.query[:200],
        "values": {},
        "interrupt": None,
    }
    background_tasks.add_task(
        _run_until_pause,
        thread_id,
        body.patient_id,
        body.clinician_id,
        body.query,
        body.patient_preferences,
    )
    return {"thread_id": thread_id}


@app.post("/plan/demo")
async def plan_demo(background_tasks: BackgroundTasks) -> dict[str, str]:
    thread_id = str(uuid4())
    prefs_path = PATIENTS_DIR / "P001" / "preferences.json"
    prefs = json.loads(prefs_path.read_text(encoding="utf-8")) if prefs_path.exists() else {}
    _threads[thread_id] = {
        "patient_id": "P001",
        "status": "running",
        "error": None,
        "query": SAMPLE_QUERY[:200],
        "values": {},
        "interrupt": None,
    }
    background_tasks.add_task(
        _run_until_pause,
        thread_id,
        "P001",
        "demo-clinician",
        SAMPLE_QUERY,
        prefs,
    )
    return {"thread_id": thread_id}


@app.get("/status/{thread_id}")
async def status(thread_id: str) -> dict[str, Any]:
    meta = _threads.get(thread_id)
    if not meta:
        raise HTTPException(404, "Unknown thread_id")
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    values: dict[str, Any] = {}
    try:
        snap = graph.get_state(config)
        values = dict(snap.values or {})
    except Exception:
        values = dict(meta.get("values") or {})
    return {
        "thread_id": thread_id,
        "status": meta.get("status"),
        "error": meta.get("error"),
        "patient_id": meta.get("patient_id") or values.get("patient_id"),
        "step_log": values.get("step_log") or [],
        "draft_plan": values.get("draft_plan") or values.get("final_plan"),
        "final_plan": values.get("final_plan"),
        "citations": values.get("citations") or [],
        "medication_review": values.get("medication_review"),
        "safety_score": values.get("safety_score"),
        "judge_feedback": values.get("judge_feedback"),
        "approval": values.get("approval"),
        "published": values.get("published"),
        "interrupt": meta.get("interrupt") or _interrupt_payload(graph, config),
    }


@app.post("/approve/{thread_id}")
async def approve(thread_id: str, body: ApproveRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    meta = _threads.get(thread_id)
    if not meta:
        raise HTTPException(404, "Unknown thread_id")
    if meta.get("status") != "pending_hitl":
        raise HTTPException(400, f"Thread not awaiting HITL (status={meta.get('status')})")
    meta["status"] = "running"
    payload = {"action": body.action, "edited_body": body.edited_body}
    background_tasks.add_task(_resume, thread_id, payload)
    return {"thread_id": thread_id, "status": "resuming"}


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8007, reload=False)


if __name__ == "__main__":
    main()
