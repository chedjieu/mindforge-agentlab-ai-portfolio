"""Offline knowledge pipeline stub (CDC → Kafka → Airflow narrative).

Hot path does not call this. Run manually to refresh local corpus metadata.
"""

from __future__ import annotations

from app.rag.retrieval import build_index


def refresh_local_index() -> int:
    chunks = build_index(force=True)
    print(f"Indexed {len(chunks)} semantic chunks from data/corpus")
    return len(chunks)


if __name__ == "__main__":
    refresh_local_index()
