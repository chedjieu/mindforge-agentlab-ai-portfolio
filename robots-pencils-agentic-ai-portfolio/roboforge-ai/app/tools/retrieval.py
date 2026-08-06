"""Hybrid retrieval over corpus."""

from __future__ import annotations

import re
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent.parent / "data" / "corpus"


def _tok(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9\-]+", (text or "").lower()) if len(t) > 2}


def hybrid_search(query: str, client_id: str, domain: str, top_k: int = 5) -> list[dict]:
    root = CORPUS / domain
    if not root.exists():
        root = CORPUS
    docs = []
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        cid = "shared"
        m = re.search(r"^client_id:\s*(\S+)", text, re.M)
        if m:
            cid = m.group(1).strip()
        if cid not in (client_id, "shared"):
            continue
        overlap = len(_tok(query) & _tok(text))
        score = overlap / max(1, len(_tok(query))) or 0.2
        docs.append(
            {
                "doc_id": path.stem,
                "text": text[:3500],
                "client_id": cid,
                "domain": domain,
                "score": round(score, 4),
            }
        )
    docs.sort(key=lambda d: d["score"], reverse=True)
    return docs[:top_k]
