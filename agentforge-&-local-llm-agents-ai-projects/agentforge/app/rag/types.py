from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, Any]

    @property
    def citation(self) -> str:
        source = self.metadata.get("source", "unknown")
        page = self.metadata.get("page", "?")
        return f"{source}#page={page}"
