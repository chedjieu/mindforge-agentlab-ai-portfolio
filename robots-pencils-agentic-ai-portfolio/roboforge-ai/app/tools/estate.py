"""Mock cloud / legacy estate tools."""

from __future__ import annotations


def assess_cloud_inventory(client_id: str, domain: str) -> dict:
    return {
        "client_id": client_id,
        "provider": "AWS",
        "resources": ["VPC", "IAM", "ECS", "Lambda", "Bedrock", "OpenSearch"],
        "readiness_score": 0.72 if domain != "migration" else 0.48,
        "recommendations": [
            "Enable Bedrock AgentCore for agent runtime",
            "Consolidate IAM roles per engagement",
            "Add Guardrails on model invocations",
        ],
    }


def assess_legacy_apps(client_id: str, domain: str) -> dict:
    return {
        "client_id": client_id,
        "stacks": ["Java", ".NET", "Python"] if domain == "migration" else ["Node.js", "Python"],
        "modernization_score": 0.55 if domain == "migration" else 0.7,
        "strategy": "strangler-fig" if domain == "migration" else "augment-with-agents",
        "dependency_hotspots": ["auth-service", "billing-batch"],
    }
