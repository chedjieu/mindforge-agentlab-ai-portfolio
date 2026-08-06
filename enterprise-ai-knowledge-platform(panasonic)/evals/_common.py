"""Shared eval helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

EVALS_DIR = Path(__file__).resolve().parent
ROOT = EVALS_DIR.parent
RUBRICS_DIR = EVALS_DIR / "rubrics"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def load_rubric(name: str) -> str:
    return (RUBRICS_DIR / name).read_text(encoding="utf-8")


def should_upload() -> bool:
    return bool(os.getenv("LANGSMITH_API_KEY", "").strip())


def parse_json_blob(text: str) -> dict[str, Any] | None:
    import re

    if not text:
        return None
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def token_count(text: str) -> int:
    return max(1, len((text or "").split()))
