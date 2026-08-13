"""AuthN/Z for local: headers. Production: OIDC-ready Principal."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.config import get_settings
from app.models.contracts import Role

REVIEWER_ROLES = {
    Role.MEDICAL_REVIEWER,
    Role.REGULATORY_REVIEWER,
    Role.QUALITY_REVIEWER,
    Role.ADMIN,
}


@dataclass
class Principal:
    tenant_id: str
    user_id: str
    role: Role


def parse_role(raw: str) -> Role:
    try:
        return Role(raw.strip().upper())
    except ValueError as exc:
        raise HTTPException(400, f"Unknown role: {raw}") from exc


def get_principal(
    x_tenant_id: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
    x_role: str | None = Header(default=None),
) -> Principal:
    settings = get_settings()
    tenant = x_tenant_id or settings.demo_tenant
    user = x_user_id or settings.demo_user
    role = parse_role(x_role or settings.demo_role)
    return Principal(tenant_id=tenant, user_id=user, role=role)


def require_reviewer(principal: Principal) -> None:
    if principal.role not in REVIEWER_ROLES and principal.role != Role.AUTHOR:
        # Authors may review in the local demo; auditors are read-only.
        if principal.role == Role.AUDITOR:
            raise HTTPException(403, "Auditors cannot approve drafts")
