"""Smoke test: generate corpus → ingest → hybrid search for PN-4421 torque."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("EGKP_MODEL", "fake")
os.environ.setdefault("EGKP_EMBEDDINGS", "fake")
os.environ.setdefault("EGKP_VECTORS", "chroma")


def main() -> None:
    from scripts.generate_synthetic_corpus import main as gen_main

    gen_main()

    from app.ingest.pipeline import run_ingest
    from app.tools.hybrid_search import hybrid_search

    result = run_ingest(load_kg=True)
    print(
        f"Ingested documents={result['documents']} chunks={result['chunks']} "
        f"vectors={result['vectors']}"
    )
    print(f"KG: {result['kg']}")

    hits = hybrid_search("PN-4421 torque", domain="manufacturing", role="engineer", k=5)
    print(f"Smoke hits ({len(hits)}):")
    for h in hits:
        print(f"  - {h['doc_id']} score={h['score']:.4f} chunk={h['chunk_id']}")

    mfg = [h for h in hits if str(h.get("metadata", {}).get("domain")) == "manufacturing"]
    if not mfg:
        # domain filter already applied; any hit is manufacturing
        mfg = hits
    if len(mfg) < 1:
        raise SystemExit("SMOKE FAIL: expected ≥ 1 manufacturing chunk for 'PN-4421 torque'")

    # Prefer evidence that mentions torque or PN-4421
    text_blob = " ".join(h["text"].lower() for h in mfg)
    if "pn-4421" not in text_blob and "torque" not in text_blob:
        raise SystemExit("SMOKE FAIL: hits lack PN-4421/torque evidence")

    print("SMOKE OK")


if __name__ == "__main__":
    main()
