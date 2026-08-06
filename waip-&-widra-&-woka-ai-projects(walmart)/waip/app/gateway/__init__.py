"""Model gateway notes — Bedrock / Vertex / fake routing."""

from app.llm import get_chat_model, get_embeddings, reset_llm_cache

__all__ = ["get_chat_model", "get_embeddings", "reset_llm_cache"]
