"""Episodic memory — similar past Q&A via pgvector or JSONL fallback."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

import psycopg

from app.llm import get_embeddings

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DEFAULT_DSN = "postgresql://postgres:postgres@localhost:5433/egkp"
TABLE = "past_qa_resolutions"


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def _postgres_available(dsn: str) -> bool:
    try:
        with psycopg.connect(dsn, connect_timeout=2) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        return True
    except Exception:
        return False


def _from_postgres(query: str, domain: str, k: int) -> list[dict] | None:
    dsn = os.getenv("POSTGRES_DSN", DEFAULT_DSN)
    if not _postgres_available(dsn):
        return None
    try:
        embedder = get_embeddings()
        vec = _vec_literal(embedder.embed_query(query))
        sql = f"""
            SELECT query_text, answer_text,
                   1 - (embedding <=> %s::vector) AS score
            FROM {TABLE}
            WHERE domain = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        with psycopg.connect(dsn, connect_timeout=3) as conn, conn.cursor() as cur:
            cur.execute(sql, (vec, domain, vec, k))
            rows = cur.fetchall()
        return [
            {
                "query_text": str(q),
                "answer_text": str(a),
                "score": float(score),
                "source": TABLE,
            }
            for q, a, score in rows
        ]
    except Exception as exc:
        logger.warning("Episodic pgvector search failed (%s) — using file fallback", exc)
        return None


def _tokenize(text: str) -> set[str]:
    return {
        t
        for t in re.findall(r"[a-z0-9]{3,}", text.lower())
        if t not in {"the", "and", "for", "with", "what", "which"}
    }


def _from_file(query: str, domain: str, k: int) -> list[dict]:
    path = DATA_DIR / domain / "historical_qa.jsonl"
    if not path.exists():
        return []

    query_tokens = _tokenize(query)
    scored: list[tuple[float, dict]] = []
    with path.open(encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            q = str(row.get("query") or row.get("query_text") or "")
            a = str(row.get("answer") or row.get("answer_text") or "")
            overlap = len(query_tokens & _tokenize(f"{q} {a}"))
            score = overlap / max(len(query_tokens), 1)
            scored.append(
                (
                    score,
                    {
                        "query_text": q,
                        "answer_text": a,
                        "score": float(score),
                        "source": f"file:{path.name}",
                    },
                )
            )
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:k]]


def similar_past_qa(query: str, domain: str, k: int = 3) -> list[dict]:
    """Return up to k similar past query → answer pairs for few-shot prompting."""
    hits = _from_postgres(query, domain or "support", k)
    if hits is not None:
        return hits
    return _from_file(query, domain or "support", k)


__all__ = ["similar_past_qa"]
