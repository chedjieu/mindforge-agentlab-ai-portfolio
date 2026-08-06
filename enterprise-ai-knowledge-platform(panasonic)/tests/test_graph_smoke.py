import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

os.environ.setdefault("EGKP_MODEL", "fake")
os.environ.setdefault("EGKP_EMBEDDINGS", "fake")
os.environ.setdefault("EGKP_JUDGE_MODEL", "fake")


def test_graph_compiles():
    from app.graph import build_graph

    g = build_graph()
    assert g is not None
