from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from app.config import Settings, get_settings

_checkpointer = None


def get_checkpointer(settings: Settings | None = None):
    """Return a durable Sqlite checkpointer, with in-memory fallback."""
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    settings = settings or get_settings()
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        import sqlite3

        from langgraph.checkpoint.sqlite import SqliteSaver

        conn = sqlite3.connect(str(settings.sqlite_path), check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
        return _checkpointer
    except Exception:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver

            # Newer API variants
            if hasattr(SqliteSaver, "from_conn_string"):
                _checkpointer = SqliteSaver.from_conn_string(str(settings.sqlite_path))
                return _checkpointer
        except Exception:
            pass

        _checkpointer = MemorySaver()
        return _checkpointer


def checkpoint_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.sqlite_path
