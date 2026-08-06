"""Resonance Technologies - AI Research Assistant (Project 1).

This package auto-loads `.env` from the project root on import so that
`RAIRA_MODEL`, `RAIRA_EMBEDDINGS`, `POSTGRES_DSN`, etc. resolve correctly when
the app is launched via `uvicorn`, `python -m`, or `pytest`. Values in `.env`
override any stale shell exports (dotenv `override=True`).
"""
from __future__ import annotations

from pathlib import Path

from app._warnings import suppress_langchain_deprecation_warnings

# Must run before any langgraph import (graph.py re-applies after langgraph loads).
suppress_langchain_deprecation_warnings()

try:
    from dotenv import load_dotenv

    _project_root = Path(__file__).resolve().parent.parent
    _env = _project_root / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
except Exception:
    pass
