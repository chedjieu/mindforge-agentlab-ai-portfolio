import os

os.environ.setdefault("ADVISEGUARD_MODEL", "fake")
os.environ.setdefault("ADVISEGUARD_EMBEDDINGS", "fake")
os.environ.setdefault("ADVISEGUARD_JUDGE_MODEL", "fake")


def test_graph_compiles():
    from app.graph import build_graph

    g = build_graph()
    assert g is not None
