from typing import Any
from pydantic import BaseModel, Field


class ThreadCreateRequest(BaseModel):
    title: str | None = None


class ThreadResponse(BaseModel):
    thread_id: str
    title: str
    created_at: str
    updated_at: str | None = None
    message_count: int = 0
    status: str = "active"
    last_run_id: str | None = None


class ThreadListResponse(BaseModel):
    threads: list[ThreadResponse]


class SendMessageRequest(BaseModel):
    message: str


class ChatMessageResponse(BaseModel):
    message_id: str
    thread_id: str
    role: str
    content: str
    created_at: str
    run_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ThreadMessagesResponse(BaseModel):
    thread_id: str
    messages: list[ChatMessageResponse]


class ToolEvent(BaseModel):
    tool_name: str
    status: str = "completed"
    started_at: str
    completed_at: str | None = None
    result_count: int = 0
    error: str | None = None


class InvestigationRunRecord(BaseModel):
    run_id: str
    thread_id: str
    status: str
    query: str
    started_at: str
    completed_at: str | None = None
    tool_events: list[ToolEvent] = Field(default_factory=list)
    evidence_count: int = 0
    error: str | None = None

