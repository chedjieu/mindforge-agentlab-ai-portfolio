"""FastAPI Associate Console — WAIP BFF."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from langgraph.types import Command
from pydantic import BaseModel

load_dotenv()

from app.graph import build_graph_with_backends
from app.rag import build_index

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "data" / "profiles"
UI = Path(__file__).resolve().parent / "ui"

app = FastAPI(title="WAIP Associate Console", version="0.1.0")
GRAPH = build_graph_with_backends()
PENDING: dict[str, dict[str, Any]] = {}


class AskRequest(BaseModel):
    query: str
    associate_id: str = "A1001"
    auto_approve: bool = False


class ApproveRequest(BaseModel):
    approved: bool = True
    note: str = ""


def _load_abac(associate_id: str) -> dict[str, Any]:
    path = PROFILES / f"{associate_id}.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return {
            "country": data.get("country", "US"),
            "state": data.get("state", "*"),
            "department": data.get("department", "*"),
            "role": data.get("role", "*"),
            "bu": data.get("bu", "*"),
            "store": data.get("store", "*"),
        }
    return {"country": "US", "state": "AR", "department": "Pharmacy", "role": "Pharmacy Tech", "bu": "US Stores"}


@app.on_event("startup")
def _startup() -> None:
    build_index()


@app.get("/", response_class=HTMLResponse)
def index() -> FileResponse:
    return FileResponse(UI / "console.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "waip"}


@app.get("/profiles")
def profiles() -> list[dict[str, Any]]:
    out = []
    if PROFILES.exists():
        for p in PROFILES.glob("*.json"):
            out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


@app.post("/ask")
def ask(body: AskRequest) -> dict[str, Any]:
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    init = {
        "associate_id": body.associate_id,
        "abac": _load_abac(body.associate_id),
        "query": body.query,
        "step_log": [],
        "evidence": [],
        "worker_results": {},
        "ticket_ids": [],
    }
    result = GRAPH.invoke(init, config=config)
    state = GRAPH.get_state(config)
    if state.tasks:
        interrupt_payload = None
        for t in state.tasks:
            if getattr(t, "interrupts", None):
                interrupt_payload = t.interrupts[0].value
                break
        if body.auto_approve:
            result = GRAPH.invoke(
                Command(resume={"approved": True, "note": "auto"}),
                config=config,
            )
            return {
                "thread_id": thread_id,
                "status": "completed",
                "result": _public(result),
            }
        PENDING[thread_id] = {"payload": interrupt_payload, "associate_id": body.associate_id}
        return {
            "thread_id": thread_id,
            "status": "awaiting_approval",
            "interrupt": interrupt_payload,
            "partial": _public(result),
        }
    return {"thread_id": thread_id, "status": "completed", "result": _public(result)}


@app.get("/pending")
def pending() -> list[dict[str, Any]]:
    return [{"thread_id": k, **v} for k, v in PENDING.items()]


@app.post("/approve/{thread_id}")
def approve(thread_id: str, body: ApproveRequest) -> dict[str, Any]:
    if thread_id not in PENDING and not body.approved:
        # still try resume
        pass
    config = {"configurable": {"thread_id": thread_id}}
    try:
        result = GRAPH.invoke(
            Command(resume={"approved": body.approved, "note": body.note}),
            config=config,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    PENDING.pop(thread_id, None)
    return {"thread_id": thread_id, "status": "completed", "result": _public(result)}


def _public(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "final_response": result.get("final_response"),
        "citations": result.get("citations"),
        "intents": result.get("intents"),
        "workers": result.get("workers"),
        "judges": result.get("judges"),
        "ticket_ids": result.get("ticket_ids"),
        "step_log": result.get("step_log"),
        "blocked": result.get("blocked", False),
    }


def main() -> None:
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8004, reload=False)


if __name__ == "__main__":
    main()
