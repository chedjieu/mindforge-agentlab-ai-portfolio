import os

os.environ.setdefault("CAREPATH_MODEL", "fake")
os.environ.setdefault("CAREPATH_EMBEDDINGS", "fake")
os.environ.setdefault("CAREPATH_JUDGE_MODEL", "fake")


def test_graph_compiles():
    from app.graph import build_graph_with_backends

    g = build_graph_with_backends()
    assert g is not None
