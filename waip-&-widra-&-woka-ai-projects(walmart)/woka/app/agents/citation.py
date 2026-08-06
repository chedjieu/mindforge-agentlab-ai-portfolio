"""Citation Agent — assemble and score citations from worker artifacts."""

from __future__ import annotations

from typing import Any


def run_citation_agent(
    *,
    retrieval: dict[str, Any] | None = None,
    sql: dict[str, Any] | None = None,
    internet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    citations: list[dict[str, Any]] = []

    for ch in (retrieval or {}).get("chunks") or []:
        citations.append(
            {
                "doc_id": ch.get("doc_id") or ch.get("chunk_id") or "doc",
                "title": ch.get("title") or ch.get("filename") or "Document",
                "page": int(ch.get("page") or 0),
                "section": ch.get("section") or "",
                "snippet": (ch.get("text") or "")[:220],
                "confidence": float(ch.get("score") or 0.8),
                "source_type": "internal",
            }
        )

    for c in (sql or {}).get("citations") or []:
        citations.append(dict(c))

    for c in (internet or {}).get("citations") or []:
        citations.append(dict(c))

    # de-dupe by doc_id+snippet prefix
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for c in citations:
        key = f"{c.get('doc_id')}|{(c.get('snippet') or '')[:40]}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)

    avg_conf = sum(float(c.get("confidence") or 0) for c in unique) / max(len(unique), 1)
    return {
        "agent": "citation",
        "citations": unique,
        "citation_count": len(unique),
        "avg_confidence": round(avg_conf, 3),
    }
