"""FastAPI dual console for AdviseGuard (:8004)."""

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

from app.graph import (
    DEMO_ADVICE_QUERY,
    build_graph,
    get_alert,
    get_customer,
    load_alerts,
    load_customers,
    make_initial_state,
)

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


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    customer_id: str = "CUST-1001"
    alert_id: str | None = None


class ApproveRequest(BaseModel):
    action: Literal["approve", "edit", "reject"]
    edited_body: str | None = None


def _has_pending_interrupt(graph, config: dict) -> bool:
    snap = graph.get_state(config)
    return any(intr for task in snap.tasks for intr in task.interrupts)


def _run_until_pause(thread_id: str, query: str, customer_id: str, alert: dict) -> None:
    graph = _get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    state = make_initial_state(
        thread_id=thread_id,
        query=query,
        customer_id=customer_id,
        txn_alert=alert,
    )
    try:
        for _ in graph.stream(state, {**config, "recursion_limit": 60}, stream_mode="updates"):
            pass
        if _has_pending_interrupt(graph, config):
            _threads[thread_id]["status"] = "pending_hitl"
        else:
            snap = graph.get_state(config).values
            _threads[thread_id]["status"] = "completed"
            _threads[thread_id]["intent"] = snap.get("intent")
            _threads[thread_id]["risk_band"] = snap.get("risk_band")
            _threads[thread_id]["published"] = snap.get("published")
    except Exception as exc:
        _threads[thread_id]["status"] = "failed"
        _threads[thread_id]["error"] = str(exc)
        logger.exception("Run failed for %s", thread_id)


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


app = FastAPI(title="AdviseGuard AI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(UI_DIR / "customer.html")


@app.get("/ops")
async def ops() -> FileResponse:
    return FileResponse(UI_DIR / "ops.html")


@app.get("/customers")
async def customers() -> list[dict]:
    return load_customers()


@app.get("/alerts")
async def alerts() -> list[dict]:
    return load_alerts()


@app.post("/ask")
async def ask(body: AskRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    alert = get_alert(body.alert_id) if body.alert_id else {}
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "customer_id": body.customer_id,
        "status": "running",
        "error": None,
        "query": body.query[:200],
        "intent": None,
        "risk_band": None,
        "published": False,
    }
    background_tasks.add_task(_run_until_pause, thread_id, body.query, body.customer_id, alert)
    return {"thread_id": thread_id}


@app.post("/ask/demo-advice")
async def demo_advice(background_tasks: BackgroundTasks) -> dict[str, str]:
    thread_id = str(uuid4())
    cust = get_customer("CUST-1001")
    _threads[thread_id] = {
        "customer_id": cust["customer_id"],
        "status": "running",
        "error": None,
        "query": DEMO_ADVICE_QUERY[:200],
        "intent": "advice",
        "risk_band": None,
        "published": False,
    }
    background_tasks.add_task(
        _run_until_pause, thread_id, DEMO_ADVICE_QUERY, cust["customer_id"], {}
    )
    return {"thread_id": thread_id}


@app.post("/fraud/demo")
async def demo_fraud(background_tasks: BackgroundTasks) -> dict[str, str]:
    alert = get_alert("ALT-FRAUD-001")
    query = str(alert.get("description") or "Investigate suspicious wire fraud")
    thread_id = str(uuid4())
    _threads[thread_id] = {
        "customer_id": alert.get("customer_id"),
        "status": "running",
        "error": None,
        "query": query[:200],
        "intent": "fraud",
        "risk_band": None,
        "published": False,
        "alert_id": alert.get("alert_id"),
    }
    background_tasks.add_task(
        _run_until_pause, thread_id, query, str(alert.get("customer_id")), alert
    )
    return {"thread_id": thread_id}


@app.get("/threads")
async def list_threads() -> list[dict]:
    return [{"thread_id": tid, **meta} for tid, meta in _threads.items()]


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


@app.get("/case/{thread_id}")
async def case_detail(thread_id: str) -> dict:
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    values = _get_graph().get_state({"configurable": {"thread_id": thread_id}}).values
    return {
        "thread_meta": _threads[thread_id],
        "intent": values.get("intent"),
        "risk_band": values.get("risk_band"),
        "risk_score": values.get("risk_score"),
        "compliance_score": values.get("compliance_score"),
        "grounding_score": values.get("grounding_score"),
        "advice_draft": values.get("advice_draft"),
        "fraud_finding": values.get("fraud_finding"),
        "support_answer": values.get("support_answer"),
        "final_response": values.get("final_response"),
        "graph_paths": values.get("graph_paths"),
        "retrieved_chunks": [
            {"id": c.get("id"), "text": (c.get("text") or "")[:400]}
            for c in (values.get("retrieved_chunks") or [])
        ],
        "approval": values.get("approval"),
        "published": values.get("published"),
        "step_log": values.get("step_log"),
    }


@app.post("/approve/{thread_id}")
async def approve(
    thread_id: str, body: ApproveRequest, background_tasks: BackgroundTasks
) -> dict:
    if thread_id not in _threads:
        raise HTTPException(status_code=404, detail="Unknown thread_id")
    _threads[thread_id]["status"] = "resuming"
    background_tasks.add_task(
        _resume, thread_id, {"action": body.action, "edited_body": body.edited_body}
    )
    return {"thread_id": thread_id, "status": "resuming"}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8004")),
        reload=False,
    )


if __name__ == "__main__":
    main()
