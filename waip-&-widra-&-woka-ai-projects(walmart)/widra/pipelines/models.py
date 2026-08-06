"""Shared ingestion models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedPage:
    page_number: int
    text: str
    is_table: bool = False


@dataclass
class ParsedDocument:
    path: str
    title: str
    pages: list[ParsedPage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    chunk_index: int
    text: str
    page_start: int
    page_end: int
    is_table: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None


@dataclass
class IngestResult:
    path: str
    doc_id: str | None = None
    source_key: str | None = None
    chunk_count: int = 0
    status: str = "pending"
    error: str | None = None
