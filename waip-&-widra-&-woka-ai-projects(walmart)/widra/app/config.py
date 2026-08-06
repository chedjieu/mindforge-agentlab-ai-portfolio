"""Environment-backed settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    widra_model: str = "fake"
    widra_embeddings: str = "fake"
    widra_memory: str = "memory"
    aws_region: str = "us-east-1"
    gcp_project: str = ""
    gcp_location: str = "us-central1"
    gcp_bucket: str = ""
    postgres_dsn: str = "postgresql://widra:widra@localhost:5433/widra"
    weaviate_url: str = "http://localhost:8081"
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "widra-docs"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    tavily_api_key: str = ""
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "widra"
    bedrock_guardrail_id: str = ""
    bedrock_guardrail_version: str = "DRAFT"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
