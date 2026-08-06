"""Environment-backed settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    woka_model: str = "fake"
    woka_embeddings: str = "fake"
    woka_memory: str = "memory"
    woka_vector_backend: str = "weaviate"  # weaviate | pinecone | local
    woka_s3_mode: str = "minio"  # minio | aws
    aws_region: str = "us-east-1"
    gcp_project: str = ""
    gcp_location: str = "us-central1"
    gcp_bucket: str = ""
    postgres_dsn: str = "postgresql://woka:woka@localhost:5434/woka"
    weaviate_url: str = "http://localhost:8082"
    s3_endpoint: str = "http://localhost:9002"
    s3_bucket: str = "woka-docs"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    pinecone_api_key: str = ""
    pinecone_index_host: str = ""
    pinecone_index: str = "woka-chunks"
    pinecone_namespace: str = "default"
    pinecone_dim: int = 64
    tavily_api_key: str = ""
    langsmith_project: str = "woka"
    neo4j_uri: str = ""
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
