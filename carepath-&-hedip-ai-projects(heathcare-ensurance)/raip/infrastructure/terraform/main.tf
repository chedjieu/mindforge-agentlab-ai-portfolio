variable "environment" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

# Sketch only — do not apply without a real backend and review.
# Intended resources: VPC, RDS Postgres (pgvector), S3, ECS/Fargate API+worker, IAM, secrets.
output "note" {
  value = "RAIP terraform is an interface sketch. See docs/architecture/LOCAL_VS_PRODUCTION.md"
}
