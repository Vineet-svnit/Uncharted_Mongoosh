"""Agent Reasoning and Tool Execution Nodes for AegisRCA."""

from typing import Any
import json
import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import ToolNode

from app.config import settings
from app.graph.state import AgentState
from app.tools.retrieval_tools import ALL_INVESTIGATION_TOOLS
from app.prompts.system_prompt import AEGIS_RCA_SYSTEM_PROMPT
from app.db.repositories.run_repository import RunRepository

logger = logging.getLogger(__name__)

run_repo = RunRepository()


def _get_llm_with_tools():
    if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key":
        llm = ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=0.1,
        )
        return llm.bind_tools(ALL_INVESTIGATION_TOOLS)
    return None


def agent_node(state: AgentState) -> dict[str, Any]:
    """Main LLM reasoning node with native tool calling."""
    messages = list(state.get("messages", []))
    plan = state.get("investigation_plan", {})
    evidence_items = state.get("evidence_items", [])
    feedback = state.get("verification_feedback")

    # If query needs clarification, skip tool calling
    if plan.get("needs_clarification"):
        clarification_msg = plan.get("clarification_question", "Could you please clarify which incident or service you would like to investigate?")
        return {
            "messages": [AIMessage(content=clarification_msg)],
        }

    # Context enrichment for reasoning
    prompt_context = (
        f"{AEGIS_RCA_SYSTEM_PROMPT}\n\n"
        f"CURRENT INVESTIGATION PLAN: {json.dumps(plan)}\n"
        f"EVIDENCE COLLECTED SO FAR: {len(evidence_items)} items.\n"
    )
    if feedback:
        prompt_context += f"VERIFICATION FEEDBACK (Address these gaps): {feedback}\n"

    sys_msg = SystemMessage(content=prompt_context)
    history_to_send = [sys_msg] + messages[-settings.max_history_messages :]

    llm_with_tools = _get_llm_with_tools()

    if llm_with_tools:
        try:
            response = llm_with_tools.invoke(history_to_send)
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"Error during LLM tool reasoning: {e}")

    # Fallback when LLM is offline or in dry-run mode:
    # Trigger appropriate tools based on plan requirements
    tool_iter = state.get("tool_iterations", 0)
    if tool_iter == 0:
        tool_calls = []
        service_id = plan.get("service_id", "checkout-api")
        incident_id = plan.get("incident_id")
        customer_id = plan.get("customer_id")

        if service_id:
            tool_calls.append(
                {
                    "name": "trace_service_dependencies",
                    "args": {"service_id": service_id},
                    "id": "call_topo_001",
                }
            )
            tool_calls.append(
                {
                    "name": "find_recent_deployments",
                    "args": {"service_id": "auth-service"},
                    "id": "call_dep_002",
                }
            )
            tool_calls.append(
                {
                    "name": "query_service_telemetry",
                    "args": {
                        "service_id": service_id,
                        "start": "2026-10-28T14:00:00Z",
                        "end": "2026-10-28T14:25:00Z",
                    },
                    "id": "call_tel_003",
                }
            )
            tool_calls.append(
                {
                    "name": "search_incident_messages",
                    "args": {"query": "DDoS Redis", "incident_id": incident_id},
                    "id": "call_slack_004",
                }
            )
        if customer_id or "sla" in plan.get("required_sources", []):
            tool_calls.append(
                {
                    "name": "retrieve_customer_sla",
                    "args": {"customer_id": customer_id or "acme-corp"},
                    "id": "call_sla_005",
                }
            )

        if tool_calls:
            return {
                "messages": [
                    AIMessage(
                        content="Initiating targeted retrieval tools across dependencies, deployments, telemetry, discussions, and SLA...",
                        tool_calls=tool_calls,
                    )
                ]
            }

    return {
        "messages": [
            AIMessage(
                content="Evidence collection complete. Proceeding to verification and report generation."
            )
        ]
    }


def execute_tools(state: AgentState) -> dict[str, Any]:
    """Execute requested tool calls, record audit events, and extract evidence items."""
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    run_id = state.get("run_id", "")
    evidence_items = list(state.get("evidence_items", []))
    tool_iterations = state.get("tool_iterations", 0) + 1

    tool_map = {t.name: t for t in ALL_INVESTIGATION_TOOLS}
    tool_messages = []

    if last_message and getattr(last_message, "tool_calls", None):
        for tc in last_message.tool_calls:
            tool_name = tc.get("name")
            tool_args = tc.get("args", {})
            call_id = tc.get("id")

            started_at = datetime.now(timezone.utc).isoformat()
            status = "completed"
            error = None
            result_count = 0
            raw_output = "{}"

            if tool_name in tool_map:
                try:
                    target_tool = tool_map[tool_name]
                    raw_output = target_tool.invoke(tool_args)

                    # Parse output into evidence records
                    try:
                        parsed = json.loads(raw_output)
                        for key in [
                            "deployments",
                            "knowledge_items",
                            "telemetry",
                            "messages",
                            "visual_evidence",
                        ]:
                            if key in parsed and isinstance(parsed[key], list):
                                evidence_items.extend(parsed[key])
                                result_count += len(parsed[key])
                        if result_count == 0 and parsed.get("status") == "success":
                            result_count = 1
                    except Exception:
                        result_count = 1
                except Exception as e:
                    status = "failed"
                    error = str(e)
                    raw_output = json.dumps({"status": "error", "message": str(e)})
            else:
                status = "failed"
                error = f"Tool '{tool_name}' not recognized."
                raw_output = json.dumps({"status": "error", "message": error})

            completed_at = datetime.now(timezone.utc).isoformat()

            # Audit logging to MongoDB investigation_runs
            if run_id:
                try:
                    run_repo.add_tool_event(
                        run_id=run_id,
                        tool_name=tool_name,
                        started_at=started_at,
                        completed_at=completed_at,
                        result_count=result_count,
                        status=status,
                        error=error,
                    )
                except Exception as err:
                    logger.warning(f"Could not persist tool event to database: {err}")

            tool_messages.append(
                ToolMessage(
                    content=raw_output,
                    tool_call_id=call_id,
                    name=tool_name,
                )
            )

    return {
        "messages": tool_messages,
        "evidence_items": evidence_items,
        "tool_iterations": tool_iterations,
    }

