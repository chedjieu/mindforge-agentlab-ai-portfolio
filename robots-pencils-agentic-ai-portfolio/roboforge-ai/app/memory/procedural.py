"""Procedural memory."""

from __future__ import annotations

import json
from pathlib import Path

PROMPTS = Path(__file__).resolve().parent.parent.parent / "data" / "prompts"
DEFAULT = (
    "Design AWS Bedrock + AgentCore architectures with Hybrid RAG, GraphRAG, "
    "HITL before production, and measurable ROI. Cite evidence. Never invent resources."
)


def get_architect_prompt(domain: str) -> str:
    path = PROMPTS / f"architect_{domain}.json"
    if not path.exists():
        return DEFAULT
    doc = json.loads(path.read_text(encoding="utf-8"))
    latest = doc.get("latest", "v1")
    return str((doc.get("versions") or {}).get(latest, {}).get("prompt") or DEFAULT)
