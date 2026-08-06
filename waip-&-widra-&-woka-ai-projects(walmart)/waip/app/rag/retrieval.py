"""Hybrid retrieval: BM25-style + dense + rerank, with ABAC metadata filters."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.llm import get_embeddings

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "data" / "corpus"


@dataclass
class Chunk:
    doc_id: str
    domain: str
    title: str
    text: str
    country: str = "US"
    state: str = "*"
    department: str = "*"
    policy_version: str = "latest"
    language: str = "en"
    tokens: set[str] = field(default_factory=set)
    vector: list[float] = field(default_factory=list)


_INDEX: list[Chunk] | None = None


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9\-]+", text.lower()) if len(t) > 1}


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1e-9
    nb = math.sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


def _bm25_score(query_tokens: set[str], doc_tokens: set[str], avgdl: float, df: dict[str, int], n: int) -> float:
    # simplified BM25-ish
    score = 0.0
    dl = max(len(doc_tokens), 1)
    k1, b = 1.2, 0.75
    for t in query_tokens:
        if t not in doc_tokens:
            continue
        n_q = df.get(t, 0) or 1
        idf = math.log(1 + (n - n_q + 0.5) / (n_q + 0.5))
        tf = 1.0
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
    return score


def _parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip().strip("\"'")
            body = parts[2].strip()
    return meta, body


def _semantic_chunks(domain: str, path: Path, body: str, meta: dict[str, str]) -> list[Chunk]:
    # split on markdown headings
    sections = re.split(r"(?m)^#{1,3}\s+", body)
    title_base = meta.get("title") or path.stem.replace("_", " ").title()
    chunks: list[Chunk] = []
    idx = 0
    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.splitlines()
        heading = lines[0].strip() if lines else title_base
        text = "\n".join(lines[1:]).strip() if len(lines) > 1 else section
        if len(text) < 40:
            text = section
        # window ~ paragraphs
        paras = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
        buf = ""
        for p in paras:
            if len(buf) + len(p) < 1800:
                buf = f"{buf}\n\n{p}".strip()
            else:
                if buf:
                    chunks.append(
                        Chunk(
                            doc_id=f"{path.stem}-{idx}",
                            domain=domain,
                            title=f"{title_base}: {heading}",
                            text=buf,
                            country=meta.get("country", "US"),
                            state=meta.get("state", "*"),
                            department=meta.get("department", "*"),
                            policy_version=meta.get("policy_version", "latest"),
                            language=meta.get("language", "en"),
                        )
                    )
                    idx += 1
                buf = p
        if buf:
            chunks.append(
                Chunk(
                    doc_id=f"{path.stem}-{idx}",
                    domain=domain,
                    title=f"{title_base}: {heading}",
                    text=buf,
                    country=meta.get("country", "US"),
                    state=meta.get("state", "*"),
                    department=meta.get("department", "*"),
                    policy_version=meta.get("policy_version", "latest"),
                    language=meta.get("language", "en"),
                )
            )
            idx += 1
    return chunks


def build_index(force: bool = False) -> list[Chunk]:
    global _INDEX
    if _INDEX is not None and not force:
        return _INDEX
    chunks: list[Chunk] = []
    if CORPUS.exists():
        for domain_dir in CORPUS.iterdir():
            if not domain_dir.is_dir():
                continue
            for path in domain_dir.glob("*.md"):
                raw = path.read_text(encoding="utf-8")
                meta, body = _parse_front_matter(raw)
                chunks.extend(_semantic_chunks(domain_dir.name, path, body, meta))
    emb = get_embeddings()
    texts = [c.text for c in chunks]
    vectors = emb.embed_documents(texts) if texts else []
    for c, v in zip(chunks, vectors):
        c.tokens = _tokenize(c.title + " " + c.text)
        c.vector = v
    _INDEX = chunks
    return chunks


def _abac_ok(chunk: Chunk, abac: dict[str, Any]) -> bool:
    country = str(abac.get("country", "US"))
    state = str(abac.get("state", "*"))
    dept = str(abac.get("department", abac.get("bu", "*")))
    if chunk.country not in ("*", country):
        return False
    if chunk.state not in ("*", state):
        return False
    if chunk.department not in ("*", dept):
        return False
    if chunk.policy_version not in ("latest", abac.get("policy_version", "latest")):
        return False
    return True


def hybrid_search(
    query: str,
    abac: dict[str, Any] | None = None,
    domain: str | None = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    abac = abac or {}
    index = [c for c in build_index() if _abac_ok(c, abac)]
    if domain:
        index = [c for c in index if c.domain == domain or domain == "search"]
    if not index:
        return []

    q_tokens = _tokenize(query)
    emb = get_embeddings()
    q_vec = emb.embed_query(query)
    n = len(index)
    avgdl = sum(len(c.tokens) for c in index) / max(n, 1)
    df: dict[str, int] = {}
    for c in index:
        for t in c.tokens:
            df[t] = df.get(t, 0) + 1

    scored: list[tuple[float, Chunk]] = []
    for c in index:
        bm = _bm25_score(q_tokens, c.tokens, avgdl, df, n)
        dense = _cosine(q_vec, c.vector)
        # RRF-ish fusion
        score = 1.0 / (60 + (1.0 / (bm + 1e-6))) + 1.0 / (60 + (1.0 / (dense + 1e-6)))
        # boost exact policy acronyms
        for acronym in ("pto", "fmla", "w-2", "w2", "loa", "hsa"):
            if acronym in q_tokens and acronym in c.tokens:
                score += 0.02
        scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    # light cross-encoder surrogate: prefer title token overlap
    reranked = sorted(
        scored[: max(top_k * 3, top_k)],
        key=lambda x: (x[0] + 0.01 * len(q_tokens & _tokenize(x[1].title))),
        reverse=True,
    )[:top_k]

    return [
        {
            "doc_id": c.doc_id,
            "domain": c.domain,
            "title": c.title,
            "text": c.text,
            "score": round(score, 4),
            "country": c.country,
            "policy_version": c.policy_version,
        }
        for score, c in reranked
    ]
