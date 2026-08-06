"""HITL + logging."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from langgraph.types import interrupt

from app.state import Approval, ForgeState

HITL_LOG = Path(__file__).resolve().parent.parent.parent / "data" / "hitl_outcomes.jsonl"


def hitl_node(state: ForgeState) -> dict:
    queued_at = datetime.now(timezone.utc)
    payload = interrupt(
        {
            "blueprint": state["blueprint"],
            "roi": state["roi"],
            "judge_scores": state["judge_scores"],
            "security_findings": state["security_findings"],
            "domain": state["domain"],
            "client_id": state["client_id"],
            "raw_pack": state["raw_pack"],
            "queued_at": queued_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    action = str(payload.get("action", "approve")).lower()
    edited = payload.get("edited_body")
    draft = dict(state["blueprint"] or {})
    if action == "approve":
        approval: Approval = "approved"
        log = "HITL: approved"
    elif action == "edit":
        approval = "edited"
        if edited:
            draft["summary"] = str(edited)
        log = "HITL: edited and approved"
    else:
        approval = "rejected"
        log = "HITL: rejected"

    try:
        HITL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with HITL_LOG.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "engagement_id": state["engagement_id"],
                        "action": action,
                        "approval": approval,
                        "judge_scores": state.get("judge_scores"),
                    }
                )
                + "\n"
            )
    except Exception:
        pass

    return {
        "approval": approval,
        "blueprint": draft,
        "step_log": state["step_log"] + [log],
    }
