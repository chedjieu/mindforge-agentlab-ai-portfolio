"""Vertex AI Agent Engine entrypoint — wraps WOKA UC-1 graph."""

from __future__ import annotations

import os
from typing import Any


def query(payload: dict[str, Any]) -> dict[str, Any]:
    os.environ.setdefault("WOKA_MODEL", os.getenv("WOKA_MODEL", "fake"))
    os.environ.setdefault("WOKA_EMBEDDINGS", os.getenv("WOKA_EMBEDDINGS", "fake"))

    from app.graph import run_uc1
    from app.observability.langsmith import configure_langsmith

    configure_langsmith()
    state = run_uc1(
        payload.get("query") or "",
        user_id=payload.get("user_id", "user-vertex"),
        role=payload.get("role", "analyst"),
        department=payload.get("department", "Supply Chain"),
        region=payload.get("region", "SE"),
    )
    return {
        "final_response": state.get("final_response") or state.get("answer"),
        "citations": state.get("citations"),
        "agents_used": state.get("agents_used"),
        "judges": state.get("judges"),
        "confidence": state.get("confidence"),
        "audit_id": state.get("audit_id"),
        "blocked": bool(state.get("blocked")),
        "runtime": "vertex-agent-engine",
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            query(
                {
                    "query": (
                        "Hurricane closed DCs in the Southeast. "
                        "Which suppliers are affected and what inventory exists within 300 miles?"
                    )
                }
            ),
            indent=2,
            default=str,
        )
    )
