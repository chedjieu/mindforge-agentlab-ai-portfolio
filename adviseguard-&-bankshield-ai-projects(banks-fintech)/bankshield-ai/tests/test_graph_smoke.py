import os

os.environ.setdefault("BANKSHIELD_MODEL", "fake")
os.environ.setdefault("BANKSHIELD_EMBEDDINGS", "fake")
os.environ.setdefault("BANKSHIELD_JUDGE_MODEL", "fake")


def test_graph_compiles():
    from app.graph import build_graph

    g = build_graph()
    assert g is not None
