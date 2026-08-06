"""Bedrock AgentCore entrypoint — wraps WOKA UC-1 graph."""

from __future__ import annotations

import os
from typing import Any


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """AgentCore-compatible invoke wrapper.

    Expects event: {query, user_id?, role?, department?, region?}
    """
    os.environ.setdefault("WOKA_MODEL", os.getenv("WOKA_MODEL", "fake"))
    os.environ.setdefault("WOKA_EMBEDDINGS", os.getenv("WOKA_EMBEDDINGS", "fake"))

    from app.graph import run_uc1
    from app.observability.langsmith import configure_langsmith

    configure_langsmith()
    state = run_uc1(
        event.get("query") or "",
        user_id=event.get("user_id", "user-agentcore"),
        role=event.get("role", "analyst"),
        department=event.get("department", "Supply Chain"),
        region=event.get("region", "SE"),
    )
    return {
        "final_response": state.get("final_response") or state.get("answer"),
        "citations": state.get("citations"),
        "agents_used": state.get("agents_used"),
        "judges": state.get("judges"),
        "confidence": state.get("confidence"),
        "audit_id": state.get("audit_id"),
        "blocked": bool(state.get("blocked")),
        "runtime": "bedrock-agentcore",
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            handler(
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
