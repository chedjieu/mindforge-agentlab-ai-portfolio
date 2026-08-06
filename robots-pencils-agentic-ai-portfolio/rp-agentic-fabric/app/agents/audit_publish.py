"""Audit publish — immutable provenance pack + client-safe summary."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.state import EngagementState

AUDIT_LOG = Path(__file__).resolve().parent.parent.parent / "data" / "audit_packs.log"

# Demo foreign markers to strip from client-facing summary
FOREIGN_MARKERS = (
    "tenant-other",
    "tenant-rival",
    "acme-health-secret",
    "northbank-secret",
    "asu-secret-roster",
)


def _client_safe_summary(text: str, tenant_id: str) -> str:
    out = text or ""
    for m in FOREIGN_MARKERS:
        out = out.replace(m, "[REDACTED]")
    for m in re.findall(r"tenant-[a-z0-9\-]+", out.lower()):
        if m != tenant_id.lower():
            out = re.sub(re.escape(m), "[REDACTED]", out, flags=re.IGNORECASE)
    return out


def audit_publish_node(state: EngagementState) -> dict:
    pack_id = f"AUD-{uuid4().hex[:10]}"
    draft = state.get("draft_plan") or {}
    summary = _client_safe_summary(str(draft.get("summary") or ""), state["tenant_id"])

    pack = {
        "audit_pack_id": pack_id,
        "engagement_id": state["engagement_id"],
        "tenant_id": state["tenant_id"],
        "vertical": state["vertical"],
        "policy_pack_id": state["policy_pack_id"],
        "regs": (state.get("guardrail_config") or {}).get("regs"),
        "reuse_decisions": state.get("reuse_decisions"),
        "judge_scores": state.get("judge_scores"),
        "approval": state.get("approval"),
        "client_safe_summary": summary,
        "architecture": draft.get("architecture"),
        "playbook_steps": draft.get("playbook_steps"),
        "citations": draft.get("citations"),
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(pack, ensure_ascii=False) + "\n")

    return {
        "published": True,
        "audit_pack_id": pack_id,
        "draft_plan": {**draft, "summary": summary},
        "step_log": state["step_log"] + [f"audit_publish: wrote {pack_id}"],
    }
