"""Case / SAR publish log."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
PUBLISH_LOG = ROOT / "data" / "published_cases.log"
HITL_LOG = ROOT / "data" / "hitl_outcomes.jsonl"


def publish_case(record: dict[str, Any]) -> str:
    PUBLISH_LOG.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **record,
    }
    with PUBLISH_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return str(PUBLISH_LOG)


def append_hitl_outcome(record: dict[str, Any]) -> None:
    HITL_LOG.parent.mkdir(parents=True, exist_ok=True)
    with HITL_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
