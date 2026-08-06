# Robots & Pencils — Agentic AI Portfolio

| Project | Folder | Port | Status |
|---------|--------|------|--------|
| **R&P Agentic Delivery Fabric** | [`rp-agentic-fabric/`](rp-agentic-fabric/) | 8002 | Implemented |
| **RoboForge AI** | [`roboforge-ai/`](roboforge-ai/) | 8003 | Implemented |

## Architecture

| Project | Architecture |
|---------|--------------|
| R&P Agentic Delivery Fabric | [`rp-agentic-fabric/docs/architecture.md`](rp-agentic-fabric/docs/architecture.md) |
| RoboForge AI | [`roboforge-ai/docs/architecture.md`](roboforge-ai/docs/architecture.md) |

### RoboForge quick start

```powershell
cd roboforge-ai
uv sync
$env:RFAI_MODEL='fake'
uv run python -m app.graph
uv run python -m app.main   # http://127.0.0.1:8003
```
