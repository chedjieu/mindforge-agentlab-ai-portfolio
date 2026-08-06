"""Optional Pinecone vector backend (REST). Falls back to local JSONL when unset."""

from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
LOCAL_PINECONE = ROOT / "data" / "local_store" / "pinecone"
DEFAULT_DIM = 64  # matches FakeEmbeddings


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class PineconeStore:
    """Upsert/query wrapper. Uses Pinecone HTTP API when configured; else local file index."""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = (os.getenv("PINECONE_API_KEY") or getattr(settings, "pinecone_api_key", "") or "").strip()
        self.index_host = (
            os.getenv("PINECONE_INDEX_HOST") or getattr(settings, "pinecone_index_host", "") or ""
        ).strip()
        self.index_name = (
            os.getenv("PINECONE_INDEX") or getattr(settings, "pinecone_index", "") or "woka-chunks"
        ).strip()
        self.namespace = (
            os.getenv("PINECONE_NAMESPACE") or getattr(settings, "pinecone_namespace", "") or "default"
        ).strip()
        self.dim = int(os.getenv("PINECONE_DIM") or getattr(settings, "pinecone_dim", DEFAULT_DIM) or DEFAULT_DIM)
        if self.api_key and self.index_host:
            self.backend = "pinecone"
        else:
            self.backend = "local"
            LOCAL_PINECONE.mkdir(parents=True, exist_ok=True)
            logger.info("PineconeStore using local fallback at %s", LOCAL_PINECONE)

    def _local_path(self) -> Path:
        return LOCAL_PINECONE / f"{self.index_name}.jsonl"

    def upsert(self, vectors: list[dict[str, Any]]) -> int:
        """vectors: [{id, values, metadata}]"""
        if not vectors:
            return 0
        if self.backend == "pinecone":
            url = f"https://{self.index_host}/vectors/upsert"
            payload = {
                "vectors": [
                    {
                        "id": v["id"],
                        "values": v["values"],
                        "metadata": v.get("metadata") or {},
                    }
                    for v in vectors
                ],
                "namespace": self.namespace,
            }
            resp = httpx.post(
                url,
                headers={"Api-Key": self.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=30.0,
            )
            resp.raise_for_status()
            return len(vectors)

        path = self._local_path()
        existing: dict[str, dict[str, Any]] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                existing[row["id"]] = row
        for v in vectors:
            existing[v["id"]] = {
                "id": v["id"],
                "values": v["values"],
                "metadata": v.get("metadata") or {},
            }
        with path.open("w", encoding="utf-8") as fh:
            for row in existing.values():
                fh.write(json.dumps(row) + "\n")
        return len(vectors)

    def query(self, vector: list[float], *, top_k: int = 5, filter: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if self.backend == "pinecone":
            url = f"https://{self.index_host}/query"
            payload: dict[str, Any] = {
                "vector": vector,
                "topK": top_k,
                "includeMetadata": True,
                "namespace": self.namespace,
            }
            if filter:
                payload["filter"] = filter
            resp = httpx.post(
                url,
                headers={"Api-Key": self.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=30.0,
            )
            resp.raise_for_status()
            matches = resp.json().get("matches") or []
            return [
                {
                    "id": m.get("id"),
                    "score": m.get("score"),
                    "metadata": m.get("metadata") or {},
                }
                for m in matches
            ]

        path = self._local_path()
        if not path.exists():
            return []
        scored: list[tuple[float, dict[str, Any]]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            meta = row.get("metadata") or {}
            if filter:
                skip = False
                for k, v in filter.items():
                    if meta.get(k) != v:
                        skip = True
                        break
                if skip:
                    continue
            score = _cosine(vector, list(row.get("values") or []))
            scored.append((score, {"id": row["id"], "score": score, "metadata": meta}))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:top_k]]


def pinecone_enabled() -> bool:
    settings = get_settings()
    backend = (os.getenv("WOKA_VECTOR_BACKEND") or getattr(settings, "woka_vector_backend", "") or "").lower()
    return backend == "pinecone"
