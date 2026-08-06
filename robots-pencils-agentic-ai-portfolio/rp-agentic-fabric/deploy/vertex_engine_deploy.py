"""Vertex AI Agent Engine deploy scaffold for RPADF."""

from __future__ import annotations

import os
from typing import Any


def build_remote_graph():
    """Build graph with Postgres checkpointer when DSN provided."""
    from app.graph import build_graph_with_backends

    dsn = os.getenv("POSTGRES_DSN", "").strip()
    if dsn:
        from langgraph.checkpoint.postgres import PostgresSaver

        saver = PostgresSaver.from_conn_string(dsn)
    else:
        import sqlite3
        from pathlib import Path

        from langgraph.checkpoint.sqlite import SqliteSaver

        path = Path(__file__).resolve().parent.parent / "checkpoints.sqlite"
        saver = SqliteSaver(sqlite3.connect(str(path), check_same_thread=False))
    return build_graph_with_backends(saver)


def predict(brief: dict[str, Any], tenant_id: str = "tenant-default") -> dict[str, Any]:
    from app.graph import make_initial_state

    graph = build_remote_graph()
    engagement_id = str(brief.get("id") or "ENG-VERTEX")
    state = make_initial_state(engagement_id, brief, tenant_id)
    config = {"configurable": {"thread_id": engagement_id}}
    for _ in graph.stream(state, config, stream_mode="updates"):
        pass
    final = graph.get_state(config).values
    return {
        "vertical": final.get("vertical"),
        "published": final.get("published"),
        "audit_pack_id": final.get("audit_pack_id"),
        "judge_scores": final.get("judge_scores"),
        "approval": final.get("approval"),
    }


def main() -> None:
    project = os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GCP_LOCATION", "us-central1")
    print(f"Vertex Agent Engine deploy scaffold (project={project}, location={location})")
    print("Wire google.cloud.aiplatform Agent Engine packaging in CI when ready.")
    print("Local predict smoke:")
    out = predict(
        {
            "id": "ENG-VTX-1",
            "title": "FERPA student onboarding",
            "body": "Canvas SIS enrollment",
        },
        "tenant-asu-demo",
    )
    print(out)


if __name__ == "__main__":
    os.environ.setdefault("RPADF_MODEL", "fake")
    main()
