"""Document / Ingestion Agent — LangGraph pipeline for PDFs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from pipelines.chunker import chunk_document
from pipelines.embed import embed_chunks
from pipelines.index import JobTracker, MetadataStore, VectorStore, index_document
from pipelines.models import IngestResult
from pipelines.parse import parse_pdf
from pipelines.upload import ObjectStore

logger = logging.getLogger(__name__)


class IngestState(TypedDict, total=False):
    paths: list[str]
    job_id: str
    results: list[dict[str, Any]]
    docs_done: int
    error: str


def _ingest_one(
    path: Path,
    *,
    object_store: ObjectStore,
    meta_store: MetadataStore,
    vector_store: VectorStore,
) -> IngestResult:
    result = IngestResult(path=str(path))
    try:
        parsed = parse_pdf(path)
        result.doc_class = parsed.doc_class
        provisional_id = str(uuid4())
        source_key = object_store.upload(path, doc_id=provisional_id, version=1)
        chunks = chunk_document(parsed)
        chunks = embed_chunks(chunks, checkpoint_key=provisional_id)
        final_id, n = index_document(
            parsed,
            chunks,
            source_key=source_key,
            meta_store=meta_store,
            vector_store=vector_store,
        )
        result.doc_id = final_id
        result.source_key = source_key
        result.chunk_count = n
        result.status = "complete"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingest failed for %s", path)
        result.status = "failed"
        result.error = str(exc)
        try:
            MetadataStore().mark_failed(
                title=path.name,
                source_key=f"failed/{path.name}",
                error=str(exc),
            )
        except Exception:  # noqa: BLE001
            pass
    return result


def node_start_job(state: IngestState) -> IngestState:
    tracker = JobTracker()
    paths = state.get("paths") or []
    job_id = tracker.start(source_path=";".join(paths[:3]), docs_total=len(paths))
    return {"job_id": job_id, "results": [], "docs_done": 0}


def node_process(state: IngestState) -> IngestState:
    paths = [Path(p) for p in state.get("paths") or []]
    object_store = ObjectStore()
    meta_store = MetadataStore()
    vector_store = VectorStore()
    tracker = JobTracker()
    results: list[dict[str, Any]] = list(state.get("results") or [])
    done = int(state.get("docs_done") or 0)
    try:
        for path in paths:
            outcome = _ingest_one(
                path,
                object_store=object_store,
                meta_store=meta_store,
                vector_store=vector_store,
            )
            results.append(outcome.__dict__)
            done += 1
            if state.get("job_id"):
                tracker.progress(state["job_id"], done)
    finally:
        vector_store.close()
    return {"results": results, "docs_done": done}


def node_finish(state: IngestState) -> IngestState:
    tracker = JobTracker()
    results = state.get("results") or []
    failed = [r for r in results if r.get("status") == "failed"]
    status = "failed" if failed and len(failed) == len(results) else "complete"
    error = "; ".join(r.get("error") or "" for r in failed) if failed else None
    if state.get("job_id"):
        tracker.finish(state["job_id"], status=status, error=error)
    return {"error": error or ""}


def build_ingestion_graph():
    g = StateGraph(IngestState)
    g.add_node("start_job", node_start_job)
    g.add_node("process", node_process)
    g.add_node("finish", node_finish)
    g.add_edge(START, "start_job")
    g.add_edge("start_job", "process")
    g.add_edge("process", "finish")
    g.add_edge("finish", END)
    return g.compile()


def run_ingestion(paths: list[Path]) -> dict[str, Any]:
    graph = build_ingestion_graph()
    return graph.invoke({"paths": [str(p) for p in paths]})
