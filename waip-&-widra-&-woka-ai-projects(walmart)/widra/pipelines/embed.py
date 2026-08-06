"""Batch embedder with simple checkpointing."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.llm import get_embeddings
from pipelines.models import Chunk

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_DIR = ROOT / "data" / "local_store" / "checkpoints"


def embed_chunks(
    chunks: list[Chunk],
    *,
    batch_size: int = 32,
    checkpoint_key: str | None = None,
) -> list[Chunk]:
    """Embed chunk texts in batches; optional checkpoint for resume."""
    emb = get_embeddings()
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = CHECKPOINT_DIR / f"{checkpoint_key}.json" if checkpoint_key else None

    start = 0
    if ckpt_path and ckpt_path.exists():
        saved = json.loads(ckpt_path.read_text(encoding="utf-8"))
        start = int(saved.get("done", 0))
        for i, vec in enumerate(saved.get("vectors", [])):
            if i < len(chunks):
                chunks[i].embedding = vec
        logger.info("Resuming embeddings from index %s", start)

    for i in range(start, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectors = emb.embed_documents([c.text for c in batch])
        for chunk, vec in zip(batch, vectors, strict=True):
            chunk.embedding = vec
        if ckpt_path:
            done = i + len(batch)
            payload = {
                "done": done,
                "vectors": [c.embedding for c in chunks[:done]],
            }
            ckpt_path.write_text(json.dumps(payload), encoding="utf-8")
        logger.debug("Embedded batch %s–%s", i, i + len(batch))

    if ckpt_path and ckpt_path.exists():
        ckpt_path.unlink()
    return chunks
