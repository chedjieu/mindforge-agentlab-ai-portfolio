"""Minimal tool-using agent — swap Bedrock ↔ Vertex via RAIRA_MODEL."""

from __future__ import annotations

import os

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool

DEFAULT_MODEL = "bedrock_converse:openai.gpt-oss-120b-1:0"
MAX_ITERATIONS = 6


@tool
def get_weather(city: str) -> str:
    """Return current weather for a city. Use this when the user asks about weather."""
    return f"It's 28C and sunny in {city}."


@tool
def search_news(topic: str) -> str:
    """Search for recent news on a topic. Use this when the user asks for news."""
    return f"Top story on {topic}: AI agents are eating tools."


TOOLS = [get_weather, search_news]
TOOL_BY_NAME = {t.name: t for t in TOOLS}


def agent_run(question: str) -> str:
    """Run a tool-calling loop until the model returns a final answer."""
    model_name = os.getenv("RAIRA_MODEL", DEFAULT_MODEL)
    llm = init_chat_model(model_name).bind_tools(TOOLS)
    messages: list = [HumanMessage(content=question)]

    for _ in range(MAX_ITERATIONS):
        ai_msg = llm.invoke(messages)
        if not ai_msg.tool_calls:
            content = ai_msg.content
            return content if isinstance(content, str) else str(content)

        messages.append(ai_msg)
        for tc in ai_msg.tool_calls:
            result = TOOL_BY_NAME[tc["name"]].invoke(tc["args"])
            messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

    return "Max iterations reached without a final answer."


if __name__ == "__main__":
    print(agent_run("What is the weather in Bangalore today and what's the latest AI news?"))
