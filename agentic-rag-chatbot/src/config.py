"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    chroma_dir: str = str(PROJECT_ROOT / "data" / "chroma")
    chroma_collection: str = "lilian_weng_kb"
    top_k: int = 4

    chunk_size: int = 1000
    chunk_overlap: int = 150

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    serper_api_key: str = ""
    urls_file: str = str(PROJECT_ROOT / "data" / "urls.txt")
    logs_dir: str = str(PROJECT_ROOT / "data" / "logs")


@lru_cache
def get_settings() -> Settings:
    return Settings()
