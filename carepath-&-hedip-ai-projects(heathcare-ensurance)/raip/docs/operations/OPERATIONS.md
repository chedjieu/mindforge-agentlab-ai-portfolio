# Operations

Full terminal command list: [COMMANDS.md](COMMANDS.md).

## Run

```bat
run.bat
```

Git Bash:

```bash
bash scripts/run.sh
```

PowerShell:

```powershell
.\scripts\run.ps1
```

Worker (optional, same ingest can run in-process on upload):

```bash
bash scripts/with-python.sh -m app.worker
```

## Health

- `GET /health` liveness
- `GET /ready` schema
- `GET /metrics` counters

## Monitoring

Structured logs with `request_id` and `tenant_id`. Redaction of SSN/MRN-like patterns. No hosted Grafana in v1.

## Alerts (production recommendation)

Error rate, ingest job DLQ (failed status), injection flag spikes, cross-tenant test failure in CI, gate BLOCKED rate.

## Rollback

Pin `RAIP_MODEL`, prompt_version, retrieval_version in provenance. Revert container tag. Prompt registry is file/policy YAML in v1.

## Backups

SQLite file copy / RDS snapshots. Object store versioning in S3. Neo4j dump.

## Incident response

1. Disable publish (`publication` always blocked via feature flag / HITL-only).  
2. Pull `GET /audit/{request_id}`.  
3. Re-ingest if corpus poisoned.  
4. Rotate model credentials if exfil suspected (injection should not have tool HTTP).

## DR

Pilot: restore SQLite + objects. Enterprise: multi-AZ Postgres, object replication, documented RPO/RTO in a real BCP — not claimed here.
