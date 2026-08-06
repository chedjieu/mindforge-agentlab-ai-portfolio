"""Slack notifier — live webhook when token set, else mock log."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "slack_notifications.log"


def notify_slack(channel: str, blocks: list[dict]) -> dict[str, Any]:
    """Post blocks to Slack, or append a mock line when SLACK_BOT_TOKEN is unset."""
    token = os.getenv("SLACK_BOT_TOKEN", "").strip()
    payload = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channel": channel,
        "blocks": blocks,
        "mode": "live" if token else "mock",
    }
    if not token:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return {"ok": True, "mode": "mock", "channel": channel}

    try:
        import urllib.request

        req = urllib.request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps({"channel": channel, "blocks": blocks}).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return {"ok": bool(body.get("ok")), "mode": "live", "channel": channel, "raw": body}
    except Exception as exc:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload["error"] = str(exc)
        payload["mode"] = "mock_fallback"
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return {"ok": False, "mode": "mock_fallback", "error": str(exc)}
