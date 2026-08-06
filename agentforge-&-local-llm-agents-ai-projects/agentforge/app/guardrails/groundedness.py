from __future__ import annotations

from app.config import get_settings
from app.rag.types import RetrievedChunk

REFUSAL = (
    "I couldn't find reliable support for that in the indexed documents. "
    "Try rephrasing or ingesting a relevant PDF."
)


def is_grounded(chunks: list[RetrievedChunk], min_score: float | None = None) -> bool:
    settings = get_settings()
    threshold = settings.min_retrieval_score if min_score is None else min_score
    if not chunks:
        return False
    return any(chunk.score >= threshold for chunk in chunks)


def grounded_or_refuse(
    chunks: list[RetrievedChunk],
    draft_answer: str,
    min_score: float | None = None,
) -> str:
    if is_grounded(chunks, min_score=min_score):
        return draft_answer
    return REFUSAL
