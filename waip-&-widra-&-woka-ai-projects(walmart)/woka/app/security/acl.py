"""RBAC / ABAC scope resolution — filters apply before retrieval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_CLEARANCE_RANK = {"internal": 0, "confidential": 1, "restricted": 2}

_ROLE_POLICIES: dict[str, list[str]] = {
    "associate": ["general_employee"],
    "analyst:supply chain": ["general_employee", "supply_chain_ops"],
    "analyst:finance": ["general_employee", "finance_analyst"],
    "analyst": ["general_employee", "supply_chain_ops"],
    "executive": ["general_employee", "supply_chain_ops", "finance_analyst", "executive"],
    "officer": ["general_employee", "supply_chain_ops", "finance_analyst"],
}


@dataclass
class AccessScope:
    user_id: str
    role: str
    department: str
    region: str
    clearance: str
    allowed_policies: list[str] = field(default_factory=list)
    allowed_regions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role,
            "department": self.department,
            "region": self.region,
            "clearance": self.clearance,
            "allowed_policies": list(self.allowed_policies),
            "allowed_regions": list(self.allowed_regions),
        }


def _clearance_for_role(role: str, department: str) -> str:
    key = role.strip().lower()
    if key == "executive":
        return "restricted"
    if key == "analyst" and "finance" in department.lower():
        return "confidential"
    if key in {"officer", "compliance"}:
        return "confidential"
    return "internal"


def resolve_scope(
    *,
    user_id: str = "user-001",
    role: str = "associate",
    department: str = "Store Ops",
    region: str = "US",
    clearance: str | None = None,
) -> AccessScope:
    role_l = role.strip().lower()
    dept_l = department.strip().lower()
    key = f"{role_l}:{dept_l}" if role_l == "analyst" else role_l
    policies = list(_ROLE_POLICIES.get(key) or _ROLE_POLICIES.get(role_l) or ["general_employee"])
    clr = clearance or _clearance_for_role(role_l, department)
    regions = ["*", "US", region.upper() if len(region) <= 3 else region]
    if region.upper() == "SE":
        regions.extend(["SE", "Southeast"])
    return AccessScope(
        user_id=user_id,
        role=role_l,
        department=department,
        region=region,
        clearance=clr,
        allowed_policies=policies,
        allowed_regions=list(dict.fromkeys(regions)),
    )


def clearance_allows(user_clearance: str, chunk_confidentiality: str) -> bool:
    u = _CLEARANCE_RANK.get((user_clearance or "internal").lower(), 0)
    c = _CLEARANCE_RANK.get((chunk_confidentiality or "internal").lower(), 0)
    return u >= c


def policy_allows(scope: AccessScope, acl_policy_name: str | None) -> bool:
    if not acl_policy_name:
        return "general_employee" in scope.allowed_policies
    return acl_policy_name in scope.allowed_policies


def region_allows(scope: AccessScope, chunk_region: str | None) -> bool:
    if not chunk_region or chunk_region in {"*", "US"}:
        return True
    return chunk_region in scope.allowed_regions or "*" in scope.allowed_regions


def chunk_authorized(
    scope: AccessScope,
    *,
    acl_policy_name: str | None,
    confidentiality: str | None,
    region: str | None,
) -> bool:
    """Pre-retrieval authorization check — never retrieve-then-filter."""
    return (
        policy_allows(scope, acl_policy_name)
        and clearance_allows(scope.clearance, confidentiality or "internal")
        and region_allows(scope, region)
    )
