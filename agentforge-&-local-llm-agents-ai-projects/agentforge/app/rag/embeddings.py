from __future__ import annotations

import ollama

from app.config import Settings, get_settings


class OllamaEmbedder:
    """Thin wrapper around Ollama embeddings for Chroma."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.client = ollama.Client(host=self.settings.ollama_host)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            response = self.client.embeddings(
                model=self.settings.ollama_embed_model,
                prompt=text,
            )
            vectors.append(response["embedding"])
        return vectors

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings(
            model=self.settings.ollama_embed_model,
            prompt=text,
        )
        return response["embedding"]
