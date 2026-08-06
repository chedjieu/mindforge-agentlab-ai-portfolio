"""Delivery publish + episodic writeback."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.memory.episodic import append_lesson
from app.state import ForgeState

PACK_LOG = Path(__file__).resolve().parent.parent.parent / "data" / "delivery_packs.log"


def delivery_publish_node(state: ForgeState) -> dict:
    pack_id = f"DP-{uuid4().hex[:10]}"
    pack = {
        "delivery_pack_id": pack_id,
        "engagement_id": state["engagement_id"],
        "client_id": state["client_id"],
        "domain": state["domain"],
        "blueprint": state.get("blueprint"),
        "roi": state.get("roi"),
        "security_findings": state.get("security_findings"),
        "judge_scores": state.get("judge_scores"),
        "roadmap": [
            "Sharpening Sprint alignment",
            "AgentCore pilot in Velocity Pod",
            "HITL production gate",
            "Pattern library writeback",
        ],
        "risk_matrix": (state.get("security_findings") or {}).get("gaps") or [],
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    PACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with PACK_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(pack, ensure_ascii=False) + "\n")

    append_lesson(
        {
            "client_id": state["client_id"],
            "domain": state["domain"],
            "engagement_id": state["engagement_id"],
            "delivery_pack_id": pack_id,
            "outcome": "approved_published",
            "summary": (state.get("blueprint") or {}).get("summary"),
            "lesson": "Reuse Bedrock AgentCore supervisor + GraphRAG + always-on HITL",
        }
    )

    return {
        "published": True,
        "delivery_pack_id": pack_id,
        "step_log": state["step_log"] + [f"delivery_publish: wrote {pack_id} + episodic lesson"],
    }
