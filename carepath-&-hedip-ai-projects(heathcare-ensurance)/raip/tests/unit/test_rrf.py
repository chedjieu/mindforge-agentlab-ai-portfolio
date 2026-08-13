from app.retrieval.hybrid import rrf_fuse


def test_rrf_prefers_consensus() -> None:
    scores = rrf_fuse([["a", "b", "c"], ["a", "c", "b"]])
    assert scores["a"] > scores["b"]
    assert scores["a"] > scores["c"]
