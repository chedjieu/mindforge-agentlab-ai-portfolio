"""Phase 1 smoke tests."""

from __future__ import annotations

import os

os.environ["WOKA_MODEL"] = "fake"
os.environ["WOKA_EMBEDDINGS"] = "fake"

from fastapi.testclient import TestClient

from app.config import get_settings
from app.llm import reset_llm_cache
from app.main import app

get_settings.cache_clear()
reset_llm_cache()
client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "woka"
    assert body["model"] == "fake"


def test_chat_uc1_stub() -> None:
    """Phase 1 smoke kept; Phase 4 wires real multi-agent path (status=ok)."""
    resp = client.post(
        "/chat",
        json={
            "query": "Hurricane closed DCs in the Southeast. Which suppliers are affected and what inventory exists within 300 miles?",
            "role": "analyst",
            "department": "Supply Chain",
            "region": "SE",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in {"ok", "stub"}
    assert "Acme" in body["answer"] or "supplier" in body["answer"].lower()
    assert len(body["citations"]) >= 1
    assert body["confidence"] > 0
