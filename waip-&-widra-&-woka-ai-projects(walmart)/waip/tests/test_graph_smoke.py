import os

os.environ.setdefault("WAIP_MODEL", "fake")
os.environ.setdefault("WAIP_EMBEDDINGS", "fake")


def test_graph_compiles():
    from app.graph import build_graph_with_backends

    g = build_graph_with_backends()
    assert g is not None
