"""Procedural memory — versioned synthesizer playbook prompts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "prompts"

DEFAULT_PROMPT = (
    "You are an R&P delivery architect. Produce a clear engagement plan with architecture "
    "bullets and playbook steps. Cite evidence ids. Never invent other clients' names, "
    "tenant ids, or proprietary details. Prefer Bedrock AgentCore patterns. Escalate "
    "regulated verticals (healthcare, finserv) for HITL."
)


def _path(vertical: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in vertical)
    return PROMPTS_DIR / f"synthesizer_{safe}.json"


def _default_doc(vertical: str) -> dict:
    return {
        "vertical": vertical,
        "latest": "v1",
        "versions": {
            "v1": {
                "prompt": DEFAULT_PROMPT,
                "created_at": "2026-01-01T00:00:00Z",
            }
        },
    }


def _load(vertical: str) -> dict:
    path = _path(vertical)
    if not path.exists():
        return _default_doc(vertical)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_synthesizer_prompt(vertical: str, version: str = "latest") -> str:
    doc = _load(vertical)
    versions = doc.get("versions") or {}
    key = doc.get("latest", "v1") if version == "latest" else version
    entry = versions.get(key) or versions.get(doc.get("latest", "v1"))
    if not entry:
        return DEFAULT_PROMPT
    return str(entry.get("prompt") or DEFAULT_PROMPT)


def set_synthesizer_prompt(vertical: str, prompt: str) -> str:
    doc = _load(vertical)
    versions = dict(doc.get("versions") or {})
    nums = []
    for key in versions:
        if key.startswith("v") and key[1:].isdigit():
            nums.append(int(key[1:]))
    next_n = (max(nums) if nums else 0) + 1
    version = f"v{next_n}"
    versions[version] = {
        "prompt": prompt,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    doc["versions"] = versions
    doc["latest"] = version
    doc["vertical"] = vertical
    path = _path(vertical)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return version
