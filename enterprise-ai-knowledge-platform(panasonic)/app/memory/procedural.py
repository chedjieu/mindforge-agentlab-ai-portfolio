"""Procedural memory — versioned answerer style prompts on disk."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "prompts"

DOMAINS = ("engineering", "manufacturing", "hr", "support", "operations")

DEFAULT_PROMPTS: dict[str, str] = {
    "manufacturing": (
        "You are an enterprise manufacturing knowledge answerer for Panasonic EGKP. "
        "Answer only from provided evidence (chunks + graph paths). "
        "Always cite sources with citation_ids that map to chunk_id/doc_id. "
        "Never invent torque values, SLAs, lot numbers, or plant policies. "
        "If evidence is missing, say so and recommend HITL."
    ),
    "engineering": (
        "You are an enterprise engineering standards answerer for Panasonic EGKP. "
        "Prefer the latest superseding standard when graph paths show SUPERSEDES. "
        "Cite every numeric claim. Never invent specifications."
    ),
    "hr": (
        "You are an HR policy answerer for Panasonic EGKP. "
        "HR answers are sensitive — recommend HITL for publish. "
        "Cite policy doc_ids. Never invent leave balances, salaries, or legal advice."
    ),
    "support": (
        "You are a product support knowledge answerer for Panasonic EGKP. "
        "Follow troubleshooting trees step-by-step. Cite KB articles. "
        "Never invent warranty extensions or refunds."
    ),
    "operations": (
        "You are an operations/SRE runbook answerer for Panasonic EGKP. "
        "Cite runbook change windows and severity procedures exactly. "
        "Never invent ETAs or unauthorized production changes."
    ),
}


def _path(domain: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in domain)
    return PROMPTS_DIR / f"answerer_{safe}.json"


def _default_doc(domain: str) -> dict:
    prompt = DEFAULT_PROMPTS.get(domain, DEFAULT_PROMPTS["support"])
    return {
        "domain": domain,
        "latest": "v1",
        "versions": {
            "v1": {
                "prompt": prompt,
                "created_at": "2026-01-01T00:00:00Z",
            }
        },
    }


def _load(domain: str) -> dict:
    path = _path(domain)
    if not path.exists():
        return _default_doc(domain)
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _save(domain: str, doc: dict) -> None:
    path = _path(domain)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
        f.write("\n")


def ensure_default_prompts() -> None:
    """Write default answerer_*.json files if missing."""
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    for domain in DOMAINS:
        path = _path(domain)
        if not path.exists():
            _save(domain, _default_doc(domain))


def get_answerer_prompt(domain: str, version: str = "latest") -> str:
    """Return the answerer style prompt for a domain (default: latest)."""
    domain = domain or "support"
    ensure_default_prompts()
    doc = _load(domain)
    versions = doc.get("versions") or {}
    key = doc.get("latest", "v1") if version == "latest" else version
    entry = versions.get(key) or versions.get(doc.get("latest", "v1"))
    if not entry:
        return DEFAULT_PROMPTS.get(domain, DEFAULT_PROMPTS["support"])
    return str(entry.get("prompt") or DEFAULT_PROMPTS["support"])


def set_answerer_prompt(domain: str, prompt: str) -> str:
    """Append a new prompt version and mark it latest. Returns the version id."""
    ensure_default_prompts()
    doc = _load(domain)
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
    doc["domain"] = domain
    _save(domain, doc)
    return version


__all__ = ["ensure_default_prompts", "get_answerer_prompt", "set_answerer_prompt"]
