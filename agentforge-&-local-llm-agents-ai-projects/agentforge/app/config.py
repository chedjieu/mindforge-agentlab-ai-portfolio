from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ollama_host: str = "http://localhost:11434"
    ollama_llm_model: str = "qwen3"
    ollama_embed_model: str = "nomic-embed-text"

    chroma_path: Path = Path("./data/chroma")
    sqlite_path: Path = Path("./data/checkpoints.db")
    assets_dir: Path = Path("./assets")
    study_note_path: Path = Path("./data/study_note.md")

    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieve_top_k: int = 4
    min_retrieval_score: float = 0.25

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    max_message_chars: int = 4000

    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    otel_exporter_otlp_endpoint: str = ""
    otel_service_name: str = "agentforge"

    rag_collection: str = "agentforge_docs"
    memory_collection: str = "agentforge_memory"

    def ensure_dirs(self) -> None:
        self.chroma_path.mkdir(parents=True, exist_ok=True)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self.study_note_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
