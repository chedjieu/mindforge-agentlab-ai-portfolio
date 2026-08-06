"""Load project `.env` early (local overrides process env)."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _ROOT / ".env"

# Local project .env wins over ambient shell vars for EGKP_* defaults.
load_dotenv(_ENV_PATH, override=True)
