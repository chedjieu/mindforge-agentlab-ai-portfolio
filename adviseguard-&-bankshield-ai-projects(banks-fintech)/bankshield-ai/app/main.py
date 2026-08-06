"""FastAPI investigator console for BankShield (:8003)."""

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

from app.graph import build_graph, get_alert, load_alerts, make_initial_state

UI_DIR = Path(__file__).resolve().parent / "ui"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_threads: dict[str, dict[str, Any]] = {}
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


class InvestigateRequest(BaseModel):
    alert_id: str | None = None
    query: str | None = None
    investigator_id: str = "inv-demo"
    alert: dict[str, Any] | None = None


class ApproveRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_body: str | None = None


class AskRequest(BaseModel):
    thread_id: str
    question: str = Field(min_length=1)


def _has_pending_interrupt(graph, config: dict) -> bool:
    snap = graph.get_state(config)
    return any(intr for task in snap.tasks for intr in task.interrupts)


def _run_until_pause(
    thread_id: str,
    alert: dict,
    query: str | None,
    investigator_id: str,
) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = make_initial_state(
        thread_id=thread_id,
        alert=alert,
        query=query,
        investigator_id=investigator_id,
    )
    try:
        for _ in graph.stream(state, config, stream_mode="updates"):
            pass
        if _has_pending_interrupt(graph, config):
            _threads[thread_id]["status"] = "pending_hitl"
        else:
            _threads[thread_id]["status"] = "completed"
            snap = graph.get_state(config).values
            _threads[thread_id]["risk_band"] = snap.get("risk_band")
            _threads[thread_id]["published"] = snap.get("published")
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)
        logger.exception("Investigation failed for %s", thread_id)


def _resume(thread_id: str, payload: dict) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    try:
        graph.invoke(Command(resume=payload), config)
        snap = graph.get_state(config).values
        _threads[thread_id]["status"] = "completed"
        _threads[thread_id]["error"] = None
        _threads[thread_id]["risk_band"] = snap.get("risk_band")
        _threads[thread_id]["published"] = snap.get("published")
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)
        logger.exception("Resume failed for %s", thread_id)


app = FastAPI(title="BankShield AI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(UI_DIR / "investigator.html")


@app.get("/alerts")
async def alerts() -> list[dict]:
    return load_alerts()


@app.post("/investigate")
async def investigate(body: InvestigateRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    alert = body.alert or get_alert(body.alert_id)
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "case_id": alert.get("case_id") or alert.get("alert_id"),
        "alert_id": alert.get("alert_id"),
        "status": "running",
        "error": None,
        "query": (body.query or alert.get("description") or "")[:200],
        "risk_band": None,
        "published": False,
    }
    background_tasks.add_task(
        _run_until_pause,
        thread_id,
        alert,
        body.query,
        body.investigator_id,
    )
    return {"thread_id": thread_id}


@app.post("/investigate/demo")
async def investigate_demo(background_tasks: BackgroundTasks) -> dict[str, str]:
    alert = get_alert("ALT-MULE-001")
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "case_id": alert.get("case_id"),
        "alert_id": alert.get("alert_id"),
        "status": "running",
        "error": None,
        "query": str(alert.get("description", ""))[:200],
        "risk_band": None,
        "published": False,
    }
    background_tasks.add_task(_run_until_pause, thread_id, alert, None, "inv-demo")
    return {"thread_id": thread_id}


@app.post("/investigate/demo-sanctions")
async def investigate_demo_sanctions(background_tasks: BackgroundTasks) -> dict[str, str]:
    alert = get_alert("ALT-OFAC-001")
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "case_id": alert.get("case_id"),
        "alert_id": alert.get("alert_id"),
        "status": "running",
        "error": None,
        "query": str(alert.get("description", ""))[:200],
        "risk_band": None,
        "published": False,
    }
    background_tasks.add_task(_run_until_pause, thread_id, alert, None, "inv-demo")
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


@app.get("/case/{thread_id}")
async def case_detail(thread_id: str) -> dict:
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    values = graph.get_state(config).values
    return {
        "thread_meta": _threads[thread_id],
        "case_id": values.get("case_id"),
        "risk_score": values.get("risk_score"),
        "risk_band": values.get("risk_band"),
        "fraud_types": values.get("fraud_types"),
        "evidence": values.get("evidence"),
        "graph_paths": values.get("graph_paths"),
        "reg_citations": [
            {"id": c.get("id"), "text": (c.get("text") or "")[:500], "metadata": c.get("metadata")}
            for c in (values.get("reg_citations") or [])
        ],
        "similar_cases": values.get("similar_cases"),
        "recommendation": values.get("recommendation"),
        "grounding_score": values.get("grounding_score"),
        "approval": values.get("approval"),
        "sar_draft": values.get("sar_draft"),
        "step_log": values.get("step_log"),
        "published": values.get("published"),
    }


@app.post("/approve/{thread_id}")
async def approve(
    thread_id: str, body: ApproveRequest, background_tasks: BackgroundTasks
) -> dict:
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    payload = {"action": body.action, "edited_body": body.edited_body}
    _threads[thread_id]["status"] = "resuming"
    background_tasks.add_task(_resume, thread_id, payload)
    return {"thread_id": thread_id, "status": "resuming"}


@app.post("/ask")
async def ask_case(body: AskRequest) -> dict:
    """Lightweight case-context Q&A (no full re-investigation)."""
    if body.thread_id not in _threads:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    detail = await case_detail(body.thread_id)
    rec = detail.get("recommendation") or {}
    answer = (
        f"Q: {body.question}\n"
        f"Case {detail.get('case_id')} risk={detail.get('risk_band')} "
        f"({detail.get('risk_score')}). "
        f"Recommendation: {rec.get('summary', 'n/a')} "
        f"Evidence: {rec.get('evidence_ids', [])}."
    )
    return {"thread_id": body.thread_id, "answer": answer}


def main() -> None:
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8003"))
    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
