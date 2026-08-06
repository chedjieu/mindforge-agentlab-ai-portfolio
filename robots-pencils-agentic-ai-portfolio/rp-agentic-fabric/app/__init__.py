"""R&P Agentic Delivery Fabric — multi-tenant GenAI compliance platform."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env", override=True)
if not os.getenv("RPADF_MODEL"):
    os.environ.setdefault("RPADF_MODEL", "fake")
if not os.getenv("RPADF_EMBEDDINGS"):
    os.environ.setdefault("RPADF_EMBEDDINGS", "fake")
