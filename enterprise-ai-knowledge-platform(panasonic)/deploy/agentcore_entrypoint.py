"""Re-export root entrypoint (Day 3 H1 prompt path deploy/agentcore_entrypoint.py)."""

from agentcore_entrypoint import app, handler

__all__ = ["app", "handler"]
