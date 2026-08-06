"""Procedural playbooks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS = ROOT / "data" / "playbooks"


def load_playbook(domain: str) -> dict[str, Any]:
    path = PLAYBOOKS / f"{domain}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"domain": domain, "steps": ["retrieve", "reason", "judge"], "summary": f"Default {domain} playbook"}
