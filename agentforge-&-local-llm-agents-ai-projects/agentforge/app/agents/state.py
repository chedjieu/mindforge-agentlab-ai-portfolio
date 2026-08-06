from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, Optional, TypedDict


class AgentState(TypedDict, total=False):
    messages: Annotated[list[dict[str, str]], operator.add]
    user_message: str
    route: Literal["research", "tools", "writer", "answer", "end"]
    tool_name: Optional[str]
    tool_args: dict[str, Any]
    context: str
    citations: list[str]
    research_notes: str
    draft: str
    answer: str
    events: Annotated[list[dict[str, Any]], operator.add]
    memories: list[str]
