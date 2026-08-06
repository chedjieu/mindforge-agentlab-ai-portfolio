"""Procedural / episodic / semantic memory."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
PLAYBOOKS = ROOT / "data" / "playbooks"
EPISODIC = ROOT / "data" / "episodic" / "lessons.jsonl"
SEMANTIC = ROOT / "data" / "semantic_facts.json"


def load_procedural(name: str) -> dict[str, Any]:
    path = PLAYBOOKS / f"{name}.yaml"
    if not path.exists():
        return {"name": name, "steps": []}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def recall_episodic(associate_id: str, query: str, limit: int = 3) -> list[dict[str, Any]]:
    if not EPISODIC.exists():
        return []
    q_toks = set(query.lower().split())
    rows: list[tuple[int, dict[str, Any]]] = []
    for line in EPISODIC.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("associate_id") not in (associate_id, "*"):
            continue
        overlap = len(q_toks & set(str(row.get("lesson", "")).lower().split()))
        rows.append((overlap, row))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in rows[:limit]]


def write_episodic(associate_id: str, lesson: str, meta: dict[str, Any] | None = None) -> None:
    EPISODIC.parent.mkdir(parents=True, exist_ok=True)
    row = {"associate_id": associate_id, "lesson": lesson, **(meta or {})}
    with EPISODIC.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def semantic_facts(keys: list[str] | None = None) -> dict[str, Any]:
    if not SEMANTIC.exists():
        return {}
    data = json.loads(SEMANTIC.read_text(encoding="utf-8"))
    if not keys:
        return data
    return {k: data[k] for k in keys if k in data}
