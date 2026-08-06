"""Demo: embed two doc chunks and print their cosine similarity."""
from __future__ import annotations

import math
from pathlib import Path

from langchain.embeddings import init_embeddings

path = Path(__file__).resolve().parents[2] / "data/sample-corpus/aws-docs/iam-rotation.md"
chunks = [c.strip() for c in path.read_text(encoding="utf-8").split("\n\n") if c.strip()][:2]
vecs = init_embeddings("bedrock:amazon.titan-embed-text-v2:0").embed_documents(chunks)
a, b = vecs[0], vecs[1]
sim = sum(x * y for x, y in zip(a, b, strict=True)) / (
    math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
)
print(f"chunks: {len(chunks)}")
print(f"cosine similarity: {sim:.4f}")
