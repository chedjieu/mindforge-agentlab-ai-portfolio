"""Re-export AgentCore entrypoint for deploy/ path."""

from agentcore_entrypoint import app, handler

__all__ = ["app", "handler"]
