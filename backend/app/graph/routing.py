"""Routing logic for LangGraph StateGraph in AegisRCA."""

from app.config import settings
from app.graph.state import AgentState


def route_after_planner(state: AgentState) -> str:
    """Decide next step after investigation planning."""
    plan = state.get("investigation_plan", {})
    if plan.get("needs_clarification"):
        return "report_generator"
    return "agent"


def route_after_agent(state: AgentState) -> str:
    """Decide whether to execute tools or transition to evidence verification."""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    tool_iterations = state.get("tool_iterations", 0)

    if (
        last_message
        and getattr(last_message, "tool_calls", None)
        and tool_iterations < settings.max_tool_iterations
    ):
        return "tools"

    return "verifier"


def route_after_verifier(state: AgentState) -> str:
    """Decide whether to loop back for targeted retrieval or generate final report."""
    feedback = state.get("verification_feedback")
    attempts = state.get("verification_attempts", 0)
    tool_iterations = state.get("tool_iterations", 0)

    # Only loop back for targeted retrieval if tools have already executed (tool_iterations > 0)
    # and feedback indicates missing information. If tool_iterations == 0 (e.g. direct text response),
    # proceed directly to report generation to prevent unwanted loops.
    if (
        feedback
        and tool_iterations > 0
        and attempts <= settings.max_verification_attempts
        and tool_iterations < settings.max_tool_iterations
    ):
        return "agent"

    return "report_generator"
