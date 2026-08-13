"""Pytest session: isolated sqlite, fake models, seeded corpus."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _raip_env(tmp_path_factory: pytest.TempPathFactory) -> None:
    db = tmp_path_factory.mktemp("db") / "raip.sqlite"
    obj = tmp_path_factory.mktemp("obj")
    os.environ["RAIP_DATABASE_URL"] = f"sqlite:///{db.as_posix()}"
    os.environ["RAIP_OBJECT_ROOT"] = str(obj)
    os.environ["RAIP_MODEL"] = "fake"
    os.environ["RAIP_JUDGE_MODEL"] = "fake"
    os.environ["RAIP_EMBEDDINGS"] = "fake"
    os.environ["RAIP_HITL"] = "evaluate"
    os.environ.pop("NEO4J_URI", None)
    from app.graph.store import reset_graph_store
    from app.llm import reset_llm_cache
    from app.storage.db import init_db, reset_engine

    reset_engine()
    reset_llm_cache()
    reset_graph_store()
    init_db()
    from scripts.seed_demo import seed

    seed()
