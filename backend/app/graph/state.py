"""LangGraph Agent State for AegisRCA."""

from typing import Any
from langgraph.graph import MessagesState


class AgentState(MessagesState):
    run_id: str
    thread_id: str

    investigation_plan: dict[str, Any]
    evidence_items: list[dict[str, Any]]
    verification_feedback: str | None

    verification_attempts: int
    tool_iterations: int

    investigation_result: dict[str, Any] | None
    investigation_status: str

