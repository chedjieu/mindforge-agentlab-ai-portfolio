"""Database helpers."""

from __future__ import annotations

from pathlib import Path

import psycopg

from app.config import get_settings

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def get_connection() -> psycopg.Connection:
    return psycopg.connect(get_settings().postgres_dsn, connect_timeout=2)


def migrate() -> None:
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.execute(sql)
        conn.commit()


def ping() -> bool:
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False
