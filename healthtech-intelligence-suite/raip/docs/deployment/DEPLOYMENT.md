# Deployment

## Local

`bash scripts/run.sh` (or `run.bat` / `.\scripts\run.ps1`) or `docker compose up --build`. See [../operations/COMMANDS.md](../operations/COMMANDS.md).

## CI

`.github/workflows/ci.yml`: ruff, mypy, pytest, golden evals, injection ≥95%.

## Cloud sketches (not applied)

- `infrastructure/terraform/` — variables for VPC, RDS, ECS
- `infrastructure/kubernetes/deployment.yaml` — API + worker
- `deploy/agentcore/entrypoint.py` — Bedrock AgentCore-shaped
- `deploy/vertex_engine/entrypoint.py` — Vertex Agent Engine-shaped

Promotion must fail when injection eval or critical pytest fails.

Environments: local, dev, staging, production via `RAIP_ENV` and separate state backends (not configured here).
