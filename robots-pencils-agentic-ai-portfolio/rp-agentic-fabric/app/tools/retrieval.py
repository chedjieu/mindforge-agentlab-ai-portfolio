"""Tenant-scoped hybrid retrieval over vertical corpora (file-based demo)."""

from __future__ import annotations

import re
from pathlib import Path

VERTICALS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "verticals"


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9\-]+", (text or "").lower()) if len(t) > 2}


def _load_docs(vertical: str) -> list[dict]:
    root = VERTICALS_DIR / vertical
    docs: list[dict] = []
    if not root.exists():
        return docs
    for path in root.rglob("*"):
        if path.suffix.lower() not in {".md", ".txt", ".json"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Optional frontmatter tenant tag: tenant_id: xxx
        tenant_id = "shared"
        m = re.search(r"^tenant_id:\s*(\S+)", text, re.MULTILINE)
        if m:
            tenant_id = m.group(1).strip()
        reusable = "reusable_ip: true" in text.lower() or "reusable_ip:true" in text.lower()
        docs.append(
            {
                "doc_id": path.stem,
                "path": str(path.relative_to(VERTICALS_DIR)),
                "text": text[:4000],
                "tenant_id": tenant_id,
                "reusable_ip": reusable,
                "vertical": vertical,
            }
        )
    return docs


def hybrid_search(
    query: str,
    tenant_id: str,
    vertical: str,
    reusable_ids: list[str] | None = None,
    top_k: int = 5,
) -> list[dict]:
    qtoks = _tokenize(query)
    reusable_ids = [r for r in (reusable_ids or []) if r]
    scored: list[dict] = []
    for doc in _load_docs(vertical):
        allowed = (
            doc["tenant_id"] == tenant_id
            or doc["tenant_id"] in ("shared", "ip-library")
            or doc.get("reusable_ip")
            or doc["doc_id"] in reusable_ids
        )
        # Hard block other tenants
        if doc["tenant_id"] not in (tenant_id, "shared", "ip-library") and not doc.get(
            "reusable_ip"
        ):
            if doc["doc_id"] not in reusable_ids:
                continue
        if not allowed and doc["doc_id"] not in reusable_ids:
            continue
        dtoks = _tokenize(doc["text"])
        overlap = len(qtoks & dtoks)
        score = overlap / max(1, len(qtoks))
        if score <= 0:
            score = 0.15 if doc["tenant_id"] in (tenant_id, "shared", "ip-library") else 0.0
        if score > 0:
            scored.append({**doc, "score": round(score, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def get_engagement_history(tenant_id: str, vertical: str, query: str) -> list[dict]:
    path = VERTICALS_DIR / vertical / "historical_engagements.jsonl"
    if not path.exists():
        return []
    rows = []
    qtoks = _tokenize(query)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        import json

        row = json.loads(line)
        if row.get("tenant_id") not in (tenant_id, "shared"):
            continue
        overlap = len(qtoks & _tokenize(str(row)))
        if overlap or row.get("tenant_id") == tenant_id:
            rows.append(row)
    return rows[:5]
