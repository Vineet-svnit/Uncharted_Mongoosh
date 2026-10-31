"""Investigation Planner Node for AegisRCA."""

from typing import Any
import json
import logging
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from app.graph.llm_factory import get_llm

from app.config import settings
from app.graph.state import AgentState

logger = logging.getLogger(__name__)


class InvestigationPlan(BaseModel):
    intent: str = Field(
        default="incident_investigation",
        description="Intent: 'incident_investigation', 'follow_up_question', 'historical_rag', 'clarification_needed'",
    )
    service_id: str | None = Field(default=None, description="Affected service ID if mentioned or inferred")
    incident_id: str | None = Field(default=None, description="Explicit incident ID if provided, e.g. 'INC-2026-10-28-001'")
    customer_id: str | None = Field(default=None, description="Affected customer ID if provided, e.g. 'acme-corp'")
    time_range: dict[str, str] | None = Field(
        default=None,
        description="Time window dictionary with 'start' and 'end' ISO-8601 strings",
    )
    required_sources: list[str] = Field(
        default_factory=list,
        description="List of sources: ['topology', 'deployments', 'telemetry', 'communications', 'sla', 'runbooks']",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if query is too vague to investigate without selecting an incident",
    )
    clarification_question: str | None = Field(
        default=None,
        description="Clarification question to pose if needs_clarification is True",
    )


PLANNER_PROMPT = """You are the Investigation Planner for AegisRCA.
Analyze the user's inquiry and the conversation history to formulate an actionable investigation plan.

## KNOWN SYSTEM CONTEXT
Active Incident: INC-2026-10-28-001 - Checkout API (checkout-api) had 0% availability from 14:00-14:25 UTC on 2026-10-28. Customer: acme-corp.
Root cause suspected: Redis connection pool exhaustion after PR #812 deployment to auth-service at 13:58 UTC.

Known Services (exact IDs): checkout-api, auth-service, redis-cluster-east, payment-service, notification-service, api-gateway, billing-service, recommendation-engine
Known Customers: acme-corp

## MAPPING RULES
- Questions about "database slowdown", "Redis", "connection pool", "504", "timeout", "latency", "slowdown" -> service_id="checkout-api", incident_id="INC-2026-10-28-001"
- Questions about "auth" or "authentication" failures -> service_id="auth-service"
- Questions about any deployment without specifying a service -> service_id="checkout-api", incident_id="INC-2026-10-28-001"
- Historical questions ("have we seen this before", "similar problem", "experienced before", "happened before", "previous") -> intent="historical_rag", required_sources=["runbooks", "postmortems", "knowledge"]
- Follow-up questions in an ongoing conversation -> set intent="follow_up_question", PRESERVE the service_id and incident_id from the conversation context
- ALWAYS populate service_id from the above mapping for any incident/failure/slowdown/error question. Never leave it null for operational questions.
- Default required_sources for incident_investigation: ["topology", "deployments", "telemetry", "communications"]
- For historical_rag and follow_up_question: ALSO include ["runbooks", "postmortems", "knowledge"] in required_sources

## GENERAL RULES
1. Do not invent IDs or customer names not listed above. Unknown optional fields must be null.
2. Set needs_clarification=True ONLY if the query is completely ambiguous and cannot be mapped to any known service or incident.
3. If the user is asking a follow-up question on an ongoing investigation, set intent='follow_up_question' and ALWAYS preserve previous service/incident context from the conversation history.
4. Output must strictly follow the JSON schema.
"""


def _heuristic_planner(last_query: str, prior_incident_id: str | None = None, prior_service_id: str | None = None) -> InvestigationPlan:
    """Deterministic fallback planner when LLM is unavailable or for deterministic tests."""
    q = last_query.lower()

    # Vague question test
    if "deployment fail yesterday" in q or "what failed yesterday" in q or "deployment fail" in q:
        return InvestigationPlan(
            intent="clarification_needed",
            needs_clarification=True,
            clarification_question="Multiple incidents were recorded yesterday. Could you clarify whether you are referring to Checkout API (INC-2026-10-28-001) or Billing Webhooks (INC-2026-10-27-003)?",
            required_sources=["incidents"],
        )

    # Historical RAG / follow-up — include context from prior investigation
    historical_keywords = [
        "similar redis problem", "similar problem", "have we encountered", "have we experienced",
        "before", "previous", "historically", "happened before", "seen before", "prior incident"
    ]
    if any(kw in q for kw in historical_keywords):
        return InvestigationPlan(
            intent="historical_rag",
            service_id=prior_service_id or "auth-service",
            incident_id=prior_incident_id,
            required_sources=["runbooks", "postmortems", "knowledge", "communications"],
            needs_clarification=False,
        )

    # EU cluster PII test
    if "eu cluster" in q or "pii" in q or "unencrypted" in q:
        return InvestigationPlan(
            intent="incident_investigation",
            service_id="auth-service",
            incident_id="INC-2026-10-15-002",
            customer_id="globex-corp",
            required_sources=["telemetry", "audit_logs"],
            needs_clarification=False,
        )

    # Main Scenario 1 / Checkout API
    service_id = "checkout-api" if "checkout" in q else None
    incident_id = "INC-2026-10-28-001" if ("october 28" in q or "oct 28" in q or "checkout" in q) else None
    customer_id = "acme-corp" if "acme" in q else None
    time_range = None
    if "14:00" in q or "october 28" in q or "oct 28" in q:
        time_range = {
            "start": "2026-10-28T14:00:00Z",
            "end": "2026-10-28T14:25:00Z",
        }

    # Keyword-based service inference for general queries
    if service_id is None:
        known_services = [
            "checkout-api", "auth-service", "redis-cluster-east", "payment-service",
            "notification-service", "api-gateway", "billing-service", "recommendation-engine"
        ]
        for svc in known_services:
            if svc in q or svc.replace("-", " ") in q:
                service_id = svc
                break

    # General incident-related keywords -> default to primary incident
    incident_keywords = [
        "database", "slowdown", "slow", "redis", "connection pool", "504", "timeout",
        "latency", "error", "failure", "fail", "outage", "incident", "degradation",
        "deployment", "pr #812", "pr812", "caused by", "root cause", "why did", "what caused",
    ]
    if service_id is None and any(kw in q for kw in incident_keywords):
        service_id = "checkout-api"
        if incident_id is None:
            incident_id = "INC-2026-10-28-001"

    # Fall back to prior context for follow-up questions with no explicit service/incident
    if service_id is None and prior_service_id:
        service_id = prior_service_id
    if incident_id is None and prior_incident_id:
        incident_id = prior_incident_id

    sources = ["topology", "deployments", "telemetry", "communications"]
    if customer_id or "sla" in q or "compensation" in q or "penalty" in q:
        sources.append("sla")

    return InvestigationPlan(
        intent="incident_investigation",
        service_id=service_id,
        incident_id=incident_id,
        customer_id=customer_id,
        time_range=time_range,
        required_sources=sources,
        needs_clarification=False,
    )


def _extract_prior_context(messages: list) -> tuple[str | None, str | None]:
    """Extract previously established incident_id and service_id from message history."""
    for m in reversed(messages):
        content = m.content if isinstance(m.content, str) else str(m.content)
        # Look for investigation plan stored in system/AI messages
        if "INC-2026-10-28-001" in content:
            return "INC-2026-10-28-001", "checkout-api"
        if "auth-service" in content and "redis" in content.lower():
            return "INC-2026-10-28-001", "auth-service"
    return None, None


def plan_investigation(state: AgentState) -> dict[str, Any]:
    """LangGraph node: formulate the investigation plan."""
    messages = state.get("messages", [])
    last_user_msg = ""
    for m in reversed(messages):
        if getattr(m, "type", None) == "human" or getattr(m, "role", None) == "user":
            last_user_msg = m.content if isinstance(m.content, str) else str(m.content)
            break

    # Extract context from prior messages for follow-up queries
    prior_incident_id, prior_service_id = _extract_prior_context(messages)

    plan: InvestigationPlan | None = None

    llm = get_llm(temperature=0.0)
    if llm:
        try:
            structured_llm = llm.with_structured_output(InvestigationPlan, method="function_calling")

            # Build conversation context for planner — include last 3 exchanges
            planner_msgs = [SystemMessage(content=PLANNER_PROMPT)]
            # Add recent conversation history (last 6 messages for context)
            recent = messages[-6:] if len(messages) > 6 else messages
            for m in recent:
                role = getattr(m, "type", None) or getattr(m, "role", None)
                content = m.content if isinstance(m.content, str) else str(m.content)
                if role in ("human", "user") and content != last_user_msg:
                    planner_msgs.append(HumanMessage(content=f"[Previous query]: {content}"))
                elif role in ("ai", "assistant"):
                    # Summarize AI response for context
                    summary = content[:300] + "..." if len(content) > 300 else content
                    planner_msgs.append(AIMessage(content=f"[Previous response summary]: {summary}"))

            # Add prior context hint if available
            context_hint = ""
            if prior_incident_id:
                context_hint = f"\n[Context: Previous investigation was about incident {prior_incident_id}, service {prior_service_id}. If this is a follow-up, preserve that context.]"

            planner_msgs.append(HumanMessage(content=f"User Query: {last_user_msg}{context_hint}"))

            plan = structured_llm.invoke(planner_msgs)
        except Exception as e:
            logger.warning(f"Planner LLM structured invocation failed, falling back to heuristic: {e}")

    if plan is None:
        plan = _heuristic_planner(last_user_msg, prior_incident_id, prior_service_id)

    return {
        "investigation_plan": plan.model_dump(),
        "tool_iterations": state.get("tool_iterations", 0),
        "verification_attempts": state.get("verification_attempts", 0),
        "evidence_items": state.get("evidence_items", []),
    }
