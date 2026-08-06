"""Append-only published plan audit log."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "data" / "published_plans.log"


def publish_plan_record(payload: dict[str, Any]) -> dict[str, Any]:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "id": f"PLAN-{uuid.uuid4().hex[:10]}",
        "ts": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return record
