"""RAIP configuration. All settings use the RAIP_ prefix."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RAIP_", env_file=".env", extra="ignore")

    env: str = "local"
    port: int = 8011
    log_level: str = "INFO"

    model: str = "fake"
    judge_model: str = "fake"
    embeddings: str = "fake"
    reranker: str = "heuristic"

    database_url: str = "sqlite:///./data/raip.sqlite"
    memory: str = "memory"
    object_root: str = "./data/objects"
    hitl: str = "required"

    demo_tenant: str = "tenant-northstar"
    demo_user: str = "author-01"
    demo_role: str = "AUTHOR"

    cost_input_per_1k: float = 0.003
    cost_output_per_1k: float = 0.015

    grounding_min: float = 0.95
    citation_min: float = 0.95
    unsupported_max: float = 0.01
    injection_min: float = 0.95

    quality_grounding_weight: float = 0.30
    quality_citation_weight: float = 0.20
    quality_coverage_weight: float = 0.15
    quality_regulatory_weight: float = 0.15
    quality_template_weight: float = 0.10
    quality_editorial_weight: float = 0.10

    max_upload_bytes: int = 20 * 1024 * 1024
    max_graph_steps: int = 24
    embed_dim: int = 64


def get_settings() -> Settings:
    return Settings()


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SAMPLE_DIR = ROOT / "sample_data"
