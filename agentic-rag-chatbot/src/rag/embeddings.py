"""OpenAI embedding model factory."""

from langchain_openai import OpenAIEmbeddings

from src.config import Settings, get_settings


def get_embeddings(settings: Settings | None = None) -> OpenAIEmbeddings:
    settings = settings or get_settings()
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return OpenAIEmbeddings(
        model=settings.openai_embedding_model,
        api_key=settings.openai_api_key,
    )
