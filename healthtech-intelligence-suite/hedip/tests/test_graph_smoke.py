import os

os.environ.setdefault("HEDIP_MODEL", "fake")
os.environ.setdefault("HEDIP_EMBEDDINGS", "fake")
os.environ.setdefault("HEDIP_JUDGE_MODEL", "fake")


def test_graph_compiles():
    from app.graph import build_graph_with_backends

    g = build_graph_with_backends()
    assert g is not None
