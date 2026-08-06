"""Demo: Bedrock guardrail blocks cooking-topic prompts when enabled."""
from __future__ import annotations

import os
import sys

from botocore.exceptions import ClientError
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage

from app.llm import DEFAULT_MODEL

TEST_PROMPT = "Give me a step-by-step recipe to make chicken biryani."


def main() -> None:
    model_name = os.getenv("RAIRA_MODEL", DEFAULT_MODEL)
    guardrail_id = os.getenv("BEDROCK_GUARDRAIL_ID", "").strip()
    guardrail_version = os.getenv("BEDROCK_GUARDRAIL_VERSION", "DRAFT").strip()

    if model_name == "fake" or not model_name.startswith("bedrock"):
        print("This demo needs a real Bedrock model (RAIRA_MODEL starting with 'bedrock').")
        sys.exit(1)

    kwargs: dict = {"region_name": os.getenv("AWS_REGION", "us-east-1")}
    if guardrail_id:
        print("=== CASE 2: GUARDRAIL ON ===")
        kwargs["guardrails"] = {
            "guardrail_identifier": guardrail_id,
            "guardrail_version": guardrail_version,
            "trace": "enabled",
        }
    else:
        print("=== CASE 1: NO GUARDRAIL (env not set) ===")

    try:
        reply = init_chat_model(model_name, **kwargs).invoke([HumanMessage(content=TEST_PROMPT)])
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ThrottlingException":
            print("\nBedrock daily token quota exceeded — wait for reset or use gpt-oss-20b in .env.")
            sys.exit(1)
        raise

    content = reply.content if isinstance(reply.content, str) else str(reply.content)
    stop_reason = (reply.response_metadata or {}).get("stopReason")
    print(f"content: {content}\nstopReason: {stop_reason}")
    print("BLOCKED by guardrail ✅" if stop_reason == "guardrail_intervened" else "Answered freely (no block).")


if __name__ == "__main__":
    main()
