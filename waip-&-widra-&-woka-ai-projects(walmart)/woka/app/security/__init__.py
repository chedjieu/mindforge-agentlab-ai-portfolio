"""Security package — RBAC/ABAC before retrieval."""

from app.security.acl import AccessScope, chunk_authorized, resolve_scope

__all__ = ["AccessScope", "chunk_authorized", "resolve_scope"]
