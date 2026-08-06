"""FastAPI entrypoint for the AI Research Assistant."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import socket
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.graph import stream_research

UI_DIR = Path(__file__).resolve().parent / "ui"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Resonance AI Research Assistant")
app.mount("/static", StaticFiles(directory=UI_DIR), name="static")

_sessions: dict[str, dict[str, object]] = {}


class ResearchRequest(BaseModel):
    question: str


async def _run_research(thread_id: str, question: str) -> None:
    queue = _sessions[thread_id]["queue"]
    assert isinstance(queue, asyncio.Queue)
    try:
        async for event in stream_research(question, thread_id):
            await queue.put(event)
    except Exception as exc:
        logger.exception("Research failed for thread %s", thread_id)
        await queue.put({"event": "error", "error": str(exc)})
    finally:
        await queue.put(None)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


@app.post("/research")
async def research(body: ResearchRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    thread_id = str(uuid4())
    _sessions[thread_id] = {"question": body.question, "queue": asyncio.Queue()}
    background_tasks.add_task(_run_research, thread_id, body.question)
    return {"thread_id": thread_id}


@app.get("/stream/{thread_id}")
async def stream(thread_id: str) -> EventSourceResponse:
    session = _sessions.get(thread_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown thread_id")

    queue = session["queue"]
    assert isinstance(queue, asyncio.Queue)

    async def event_generator():
        while True:
            event = await queue.get()
            if event is None:
                break
            yield {"data": json.dumps(event, default=str)}

    return EventSourceResponse(event_generator())


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _server_already_running(host: str, port: int) -> bool:
    """True if our app is already serving on this host:port."""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"http://{host}:{port}/", timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def main() -> None:
    """Dev server — run with: uv run python -m app.main"""
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "").lower() in ("1", "true", "yes")

    if _port_in_use(host, port):
        url = f"http://{host}:{port}"
        if _server_already_running(host, port):
            print(
                f"\n  Server already running at {url}\n"
                "  Open that URL in your browser (no need to start again).\n"
            )
            sys.exit(0)
        print(
            f"\nERROR: Port {port} is in use on {host} by another process.\n"
            "Free the port in PowerShell:\n"
            f"  netstat -ano | findstr :{port}\n"
            "  taskkill /PID <pid> /F\n"
            f"\nOr use a different port:  set PORT=8001  (cmd)  /  $env:PORT=8001  (PowerShell)\n",
            file=sys.stderr,
        )
        sys.exit(1)

    url = f"http://{host}:{port}"
    print(f"\n  Resonance AI Research Assistant\n  Open in browser: {url}\n  Press Ctrl+C to stop.\n")

    # reload=False by default — reload is unreliable on Windows paths with () and &
    if reload:
        app_dir = str(Path(__file__).resolve().parent)
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=True,
            reload_dirs=[app_dir],
        )
    else:
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
