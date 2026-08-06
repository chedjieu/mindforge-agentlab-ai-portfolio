"""Batch ingest — concurrent PDF ingestion for scale demos."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

if os.getenv("WOKA_INGEST_CLOUD", "").lower() not in {"1", "true", "yes"}:
    os.environ.setdefault("WOKA_EMBEDDINGS", "fake")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pipelines.batch_ingest")

ROOT = Path(__file__).resolve().parents[1]


def collect_pdfs(
    *,
    dirs: list[Path] | None = None,
    files: list[Path] | None = None,
    manifest: Path | None = None,
) -> list[Path]:
    paths: list[Path] = []
    for d in dirs or []:
        if d.is_dir():
            paths.extend(sorted(d.glob("*.pdf")))
    for f in files or []:
        if f.is_file():
            paths.append(f)
    if manifest and manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for item in data.get("files") or data if isinstance(data, list) else []:
            p = Path(item) if isinstance(item, str) else Path(item.get("path", ""))
            if not p.is_absolute():
                p = (manifest.parent / p).resolve()
            if p.is_file():
                paths.append(p)
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _ingest_one(path: Path) -> dict[str, Any]:
    from app.agents.document import run_ingestion

    t0 = time.perf_counter()
    try:
        result = run_ingestion([path])
        rows = result.get("results") or []
        row = rows[0] if rows else {"status": "failed", "error": "empty"}
        return {
            "path": str(path),
            "status": row.get("status"),
            "doc_id": row.get("doc_id"),
            "chunk_count": row.get("chunk_count", 0),
            "error": row.get("error"),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
            "job_id": result.get("job_id"),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "path": str(path),
            "status": "failed",
            "error": str(exc),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }


def run_batch(
    pdfs: list[Path],
    *,
    workers: int = 4,
) -> dict[str, Any]:
    from app.llm import reset_llm_cache
    from pipelines.index import JobTracker

    reset_llm_cache()
    workers = max(1, min(int(workers), 16))
    tracker = JobTracker()
    job_id = tracker.start(source_path="batch", docs_total=len(pdfs))
    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_ingest_one, p): p for p in pdfs}
        done = 0
        for fut in as_completed(futures):
            results.append(fut.result())
            done += 1
            tracker.progress(job_id, done)
            logger.info("[%d/%d] %s -> %s", done, len(pdfs), futures[fut].name, results[-1].get("status"))

    ok = sum(1 for r in results if r.get("status") == "complete")
    failed = [r for r in results if r.get("status") != "complete"]
    status = "complete" if not failed else ("complete" if ok / max(len(results), 1) >= 0.98 else "failed")
    tracker.finish(job_id, status=status, error=None if not failed else f"{len(failed)} failed")
    elapsed = time.perf_counter() - t0
    return {
        "job_id": job_id,
        "docs_total": len(results),
        "docs_ok": ok,
        "docs_failed": len(failed),
        "chunks": sum(int(r.get("chunk_count") or 0) for r in results),
        "workers": workers,
        "elapsed_sec": round(elapsed, 3),
        "docs_per_sec": round(len(results) / max(elapsed, 1e-6), 3),
        "results": sorted(results, key=lambda r: r.get("path") or ""),
        "status": status,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WOKA concurrent batch ingest")
    parser.add_argument("--dir", type=Path, action="append", default=[], help="PDF directory (repeatable)")
    parser.add_argument("--file", type=Path, action="append", default=[], help="PDF file (repeatable)")
    parser.add_argument("--manifest", type=Path, help="JSON manifest of file paths")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    dirs = args.dir or ([ROOT / "data" / "sample_docs"] if not args.file and not args.manifest else [])
    pdfs = collect_pdfs(dirs=dirs, files=args.file, manifest=args.manifest)
    if not pdfs:
        logger.error("No PDFs found")
        return 1

    logger.info("Batch ingest %d PDF(s) with %d workers", len(pdfs), args.workers)
    result = run_batch(pdfs, workers=args.workers)
    print(
        f"job_id={result['job_id']} ok={result['docs_ok']}/{result['docs_total']} "
        f"chunks={result['chunks']} elapsed={result['elapsed_sec']}s "
        f"rate={result['docs_per_sec']}/s"
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
