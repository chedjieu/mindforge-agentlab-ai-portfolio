"""Vertex AI Agent Engine-shaped entrypoint (sketch)."""

from __future__ import annotations

from deploy.agentcore.entrypoint import handler


def predict(instances: list[dict]) -> list[dict]:
    return [handler(inst) for inst in instances]
