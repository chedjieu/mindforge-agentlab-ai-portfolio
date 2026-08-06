"""Deploy panasonic-egkp to Vertex AI Agent Engine."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> None:
    try:
        from dotenv import load_dotenv

        env_path = _ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)
    except Exception:
        pass

    import vertexai
    from vertexai import agent_engines

    from app.graph import build_graph

    vertexai.init(
        project=os.environ["GCP_PROJECT"],
        location=os.environ.get("GCP_LOCATION", "us-central1"),
        staging_bucket=f"gs://{os.environ['GCP_BUCKET']}",
    )

    langgraph_agent = agent_engines.LanggraphAgent(
        model="gemini-2.5-pro",
        runnable=build_graph(),
        enable_tracing=True,
    )

    deployed = agent_engines.create(
        langgraph_agent,
        requirements=[
            "langgraph>=1.2,<2",
            "langchain-google-vertexai",
            "psycopg[binary]",
            "pydantic>=2",
            "chromadb",
            "neo4j",
            "pyyaml",
        ],
        display_name="panasonic-egkp",
    )
    print("Deployed:", deployed.resource_name)


if __name__ == "__main__":
    main()
