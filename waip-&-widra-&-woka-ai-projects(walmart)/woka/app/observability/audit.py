"""In-memory + Postgres audit trail."""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import ping as db_ping

_LOCK = threading.Lock()
_MEMORY: list[dict[str, Any]] = []
_MAX_MEMORY = 500


def write_audit(
    *,
    user_id: str,
    action: str,
    query_text: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "audit_id": str(uuid.uuid4()),
        "user_id": user_id,
        "action": action,
        "query_text": query_text,
        "details": details or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _LOCK:
        _MEMORY.insert(0, record)
        del _MEMORY[_MAX_MEMORY:]

    if db_ping():
        try:
            from app.db import get_connection

            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO audit_log (audit_id, user_id, action, query_text, details)
                    VALUES (%s::uuid, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        record["audit_id"],
                        user_id,
                        action,
                        query_text,
                        json.dumps(details or {}),
                    ),
                )
                conn.commit()
        except Exception:  # noqa: BLE001
            pass
    return record


def list_audits(limit: int = 50, action: str | None = None) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 200))
    if db_ping():
        try:
            from app.db import get_connection

            with get_connection() as conn:
                if action:
                    rows = conn.execute(
                        """
                        SELECT audit_id::text, user_id, action, query_text, details, created_at
                        FROM audit_log WHERE action = %s
                        ORDER BY created_at DESC LIMIT %s
                        """,
                        (action, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        """
                        SELECT audit_id::text, user_id, action, query_text, details, created_at
                        FROM audit_log ORDER BY created_at DESC LIMIT %s
                        """,
                        (limit,),
                    ).fetchall()
                return [
                    {
                        "audit_id": r[0],
                        "user_id": r[1],
                        "action": r[2],
                        "query_text": r[3],
                        "details": r[4] if isinstance(r[4], dict) else json.loads(r[4] or "{}"),
                        "created_at": r[5].isoformat() if hasattr(r[5], "isoformat") else str(r[5]),
                    }
                    for r in rows
                ]
        except Exception:  # noqa: BLE001
            pass

    with _LOCK:
        items = list(_MEMORY)
    if action:
        items = [i for i in items if i.get("action") == action]
    return items[:limit]
