"""Security Agent — resolve AccessScope before any retrieval."""

from __future__ import annotations

from typing import Any

from app.security.acl import AccessScope, resolve_scope


def run_security_agent(
    *,
    user_id: str = "user-001",
    role: str = "associate",
    department: str = "Store Ops",
    region: str = "US",
    clearance: str | None = None,
) -> dict[str, Any]:
    scope = resolve_scope(
        user_id=user_id,
        role=role,
        department=department,
        region=region,
        clearance=clearance,
    )
    return {
        "agent": "security",
        "scope": scope.to_dict(),
        "allowed_policies": scope.allowed_policies,
        "clearance": scope.clearance,
    }


def scope_from_request(
    *,
    user_id: str = "user-001",
    role: str = "associate",
    department: str = "Store Ops",
    region: str = "US",
    clearance: str | None = None,
) -> AccessScope:
    return resolve_scope(
        user_id=user_id,
        role=role,
        department=department,
        region=region,
        clearance=clearance,
    )
