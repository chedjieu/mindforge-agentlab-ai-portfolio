from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    pdf_path: Optional[str] = Field(
        default=None,
        description="Optional path relative to assets dir or absolute path",
    )


class IngestResponse(BaseModel):
    status: str
    documents_indexed: int
    collection: str
    source: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    thread_id: str = Field(default="default")
    stream: bool = True


class ChatResponse(BaseModel):
    thread_id: str
    answer: str
    route: Optional[str] = None
    citations: list[str] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    ollama_host: str
    chroma_ready: bool
    documents_indexed: int


class EvalRequest(BaseModel):
    run_sample: bool = True


class EvalCaseResult(BaseModel):
    question: str
    answer: str
    groundedness: Optional[float] = None
    relevance: Optional[float] = None
    notes: str = ""


class EvalResponse(BaseModel):
    status: str
    results: list[EvalCaseResult]


class ResearchNotes(BaseModel):
    facts: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)


class StudyNote(BaseModel):
    title: str
    markdown: str
    sections: list[str] = Field(default_factory=list)


class FinalAnswer(BaseModel):
    answer: str
    citations: list[str] = Field(default_factory=list)
    used_tools: list[str] = Field(default_factory=list)
