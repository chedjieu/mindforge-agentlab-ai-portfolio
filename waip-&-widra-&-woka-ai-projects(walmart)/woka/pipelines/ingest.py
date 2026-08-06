"""CLI: ingest PDFs into WOKA storage.

Usage:
  uv run python -m pipelines.ingest --dir data/sample_docs/
  uv run python -m pipelines.ingest --file data/sample_docs/01_se_dc_contingency_sop.pdf
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Prefer offline embeddings for local ingest unless explicitly overridden
if os.getenv("WOKA_INGEST_CLOUD", "").lower() not in {"1", "true", "yes"}:
    os.environ["WOKA_EMBEDDINGS"] = "fake"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pipelines.ingest")


def _collect_pdfs(dir_path: Path | None, file_path: Path | None) -> list[Path]:
    paths: list[Path] = []
    if file_path:
        paths.append(file_path)
    if dir_path:
        paths.extend(sorted(dir_path.glob("*.pdf")))
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WOKA PDF ingestion pipeline")
    parser.add_argument("--dir", type=Path, help="Directory of PDFs")
    parser.add_argument("--file", type=Path, help="Single PDF path")
    parser.add_argument("--json", action="store_true", help="Print full JSON result")
    args = parser.parse_args(argv)

    if not args.dir and not args.file:
        parser.error("Provide --dir and/or --file")

    pdfs = _collect_pdfs(args.dir, args.file)
    if not pdfs:
        logger.error("No PDFs found")
        return 1

    from app.agents.document import run_ingestion
    from app.llm import reset_llm_cache

    reset_llm_cache()
    logger.info("Ingesting %d PDF(s)...", len(pdfs))
    result = run_ingestion(pdfs)
    results = result.get("results") or []
    ok = sum(1 for r in results if r.get("status") == "complete")
    failed = [r for r in results if r.get("status") == "failed"]
    chunks = sum(int(r.get("chunk_count") or 0) for r in results)

    print(f"job_id={result.get('job_id')}")
    print(f"docs_ok={ok}/{len(results)} chunks={chunks}")
    if failed:
        print(f"failed={len(failed)}")
        for r in failed:
            print(f"  - {r.get('path')}: {r.get('error')}")
    if args.json:
        print(json.dumps(result, indent=2, default=str))

    fail_rate = (len(failed) / len(results)) if results else 1.0
    return 1 if fail_rate > 0.02 and failed else 0


if __name__ == "__main__":
    sys.exit(main())
