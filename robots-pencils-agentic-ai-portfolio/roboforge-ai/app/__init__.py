"""RoboForge AI — autonomous enterprise AI delivery platform."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True)
os.environ.setdefault("RFAI_MODEL", "fake")
os.environ.setdefault("RFAI_EMBEDDINGS", "fake")
