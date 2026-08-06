"""Phase 6 — batch ingest, pinecone/S3 adapters, deploy entrypoints, P95."""

from __future__ import annotations

import os
from pathlib import Path

os.environ["WOKA_MODEL"] = "fake"
os.environ["WOKA_EMBEDDINGS"] = "fake"

from fastapi.testclient import TestClient

from app.config import get_settings
from app.llm import reset_llm_cache
from app.main import app
from evals.latency_smoke import run_latency_smoke
from pipelines.pinecone_store import PineconeStore

get_settings.cache_clear()
reset_llm_cache()
client = TestClient(app)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample_docs"


def test_health_phase6() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["phase"] == 6
    assert "backends" in body
    assert "deploy" in body


def test_latency_p95_under_5s() -> None:
    result = run_latency_smoke(iterations=3, p95_budget_sec=5.0)
    assert result["pass"] is True
    assert result["p95_sec"] < 5.0


def test_pinecone_local_upsert_query() -> None:
    store = PineconeStore()
    assert store.backend in {"local", "pinecone"}
    n = store.upsert(
        [
            {
                "id": "c-test-1",
                "values": [0.1] * store.dim,
                "metadata": {"doc_id": "d1", "text": "Acme Logistics inventory MEM-03"},
            }
        ]
    )
    assert n == 1
    hits = store.query([0.1] * store.dim, top_k=3)
    assert hits
    assert hits[0]["id"] == "c-test-1"


def test_batch_ingest_cli_api() -> None:
    if not SAMPLE.exists() or not list(SAMPLE.glob("*.pdf")):
        # still exercise collect/run with empty → error path via API
        resp = client.post("/ingest/batch", json={"dir": str(SAMPLE), "workers": 2})
        assert resp.status_code == 200
        return
    resp = client.post("/ingest/batch", json={"dir": str(SAMPLE), "workers": 2})
    assert resp.status_code == 200
    body = resp.json()
    assert body["docs_ok"] >= 1
    assert body["status"] == "complete"


def test_agentcore_entrypoint() -> None:
    from deploy.agentcore.entrypoint import handler

    out = handler(
        {
            "query": "Hurricane closed DCs in the Southeast. Which suppliers are affected?",
            "role": "analyst",
            "department": "Supply Chain",
            "region": "SE",
        }
    )
    assert out["runtime"] == "bedrock-agentcore"
    assert out.get("final_response")
    assert out.get("citations")


def test_vertex_entrypoint() -> None:
    from deploy.vertex_engine.entrypoint import query

    out = query(
        {
            "query": "Hurricane closed DCs in the Southeast. What inventory exists within 300 miles?",
            "role": "analyst",
            "department": "Supply Chain",
            "region": "SE",
        }
    )
    assert out["runtime"] == "vertex-agent-engine"
    assert out.get("final_response")
