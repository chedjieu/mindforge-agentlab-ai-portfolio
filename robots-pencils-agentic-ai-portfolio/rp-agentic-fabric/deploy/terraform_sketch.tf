# Terraform sketch — shared control plane (not applied in v1 demo)

variable "project_prefix" {
  type    = string
  default = "rpadf"
}

# Per-tenant IAM roles and Vault-managed secrets would be defined here.
# AWS: ECS/EKS control plane + Bedrock AgentCore runtimes
# GCP: Vertex Agent Engine for GCP-committed engagements

output "note" {
  value = "Scaffold only — wire real modules per engagement cloud commitment"
}
