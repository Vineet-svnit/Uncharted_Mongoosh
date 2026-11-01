"""Investigation Planner Node for AegisRCA."""

from typing import Any
import re
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
        description=(
            "Inquiry intent: "
            "'incident_investigation' (investigating an incident or service issue), "
            "'historical_rag' (inquiring about past postmortems, runbooks, or similar incidents), "
            "'follow_up_question' (follow-up in an ongoing thread), "
            "'conversation_memory' (inquiries about ongoing chat history, user identity e.g. 'what is my name', or past turns), "
            "'general_sre_inquiry' (greetings, architectural concepts, general SRE questions, or code requests not requiring database lookup), "
            "'out_of_domain' (questions completely unrelated to SRE, cloud infrastructure, or the ongoing conversation), "
            "'clarification_needed' (ambiguous query referring to unspecified incidents)"
        ),
    )
    service_id: str | None = Field(default=None, description="Affected service ID if mentioned or inferred from query/context")
    incident_id: str | None = Field(default=None, description="Explicit incident ID if provided, e.g. 'INC-2026-10-28-001'")
    customer_id: str | None = Field(default=None, description="Affected customer ID if provided")
    time_range: dict[str, str] | None = Field(
        default=None,
        description="Time window dictionary with 'start' and 'end' ISO-8601 strings",
    )
    required_sources: list[str] = Field(
        default_factory=list,
        description="List of sources: ['topology', 'deployments', 'telemetry', 'communications', 'sla', 'runbooks', 'incidents', 'visual']",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if query is too vague to investigate without selecting an incident",
    )
    clarification_question: str | None = Field(
        default=None,
        description="Clarification question to pose if needs_clarification is True",
    )


PLANNER_PROMPT = """You are the Investigation Planner for AegisRCA, an autonomous SRE & Root Cause Analysis assistant.
Analyze the user's inquiry and the conversation history to formulate an actionable investigation plan.

## INTENT TAXONOMY:
- conversation_memory: Inquiries about the conversation state, previous messages ("what did I ask earlier?", "what was the first code I asked?"), user identity ("what is my name?", "who am I?"), or meta-dialogue. These are 100% in-domain conversation questions. required_sources=[]
- general_sre_inquiry: Greetings ("hi", "who are you"), general conceptual SRE / architectural questions, or requests for production SRE / infrastructure automation scripts (e.g. health checks, connection pool monitors, Prometheus exporters). NEVER use for academic DSA or LeetCode questions. required_sources=[]
- incident_investigation: Investigating a specific production incident, service failure, outage, or performance degradation.
- historical_rag: Inquiries asking about previous similar incidents, historical postmortems, or runbooks ("have we seen this before", "similar problem", "previous outage").
- follow_up_question: Continuing or drilling into a previously investigated incident from conversation history.
- out_of_domain: The query is completely external and unrelated to SRE, cloud infrastructure, OR the conversation state. This explicitly includes:
  * General trivia, cooking recipes, movies, sports, politics, weather.
  * Academic Data Structures & Algorithms (DSA), competitive programming, or LeetCode questions (e.g. 2-Sum, 3-Sum, binary trees, sorting algorithms, dynamic programming puzzles).
  required_sources=[]
- clarification_needed: The user asks an operational question but it is completely ambiguous (e.g. "what broke?") and multiple incidents could match.

## EXTRACTION GUIDELINES:
1. Extract service_id, incident_id, customer_id, and time_range strictly from the user's message or the conversation history.
2. If not mentioned or established in context, leave them as null. NEVER hallucinate or assume arbitrary IDs.
3. For follow_up_question: Always preserve service_id, incident_id, and customer_id established in the conversation context.
4. For conversation_memory, general_sre_inquiry, and out_of_domain: required_sources is empty [].
5. Set required_sources based on what is genuinely required:
   - topology: Service dependencies and call graphs
   - deployments: Recent code releases, PRs, and config changes
   - telemetry: Metric time-series (error rates, latency, saturation)
   - communications: Slack/chat discussions
   - sla: Customer contract terms and credit rules
   - runbooks: Engineering knowledge and historical postmortems
   - incidents: Listing or finding known incident records

Output must strictly conform to the InvestigationPlan JSON schema.
"""


def _heuristic_planner(last_query: str, prior_incident_id: str | None = None, prior_service_id: str | None = None) -> InvestigationPlan:
    """Deterministic fallback planner when LLM is unavailable or for deterministic tests."""
    q = last_query.lower().strip()

    # Conversation memory & user identity check
    memory_keywords = [
        "what is my name", "what's my name", "who am i", "my name",
        "what did i ask", "what was the first", "what was my first",
        "what did i say", "previous question", "earlier question",
        "first code", "what was the code", "what code did i",
        "what was its response", "what was the response",
        "summarize our conversation", "what have we talked about"
    ]
    if any(kw in q for kw in memory_keywords):
        return InvestigationPlan(
            intent="conversation_memory",
            required_sources=[],
            needs_clarification=False,
        )

    # Academic DSA / LeetCode / Algorithmic Coding Check (STRICT HARDRALILING: OUT OF DOMAIN)
    dsa_keywords = [
        "3 sum", "3sum", "two sum", "2sum", "leetcode", "dsa", "data structure",
        "binary search tree", "bst", "bubble sort", "quick sort", "quicksort", "merge sort",
        "mergesort", "insertion sort", "linked list", "binary tree", "trie", "knapsack",
        "dynamic programming", "tower of hanoi", "fibonacci", "palindrome", "prime number",
        "invert a binary tree", "matrix multiplication", "depth first search", "breadth first search",
        "dijkstra", "topological sort", "graph coloring", "competitive programming"
    ]
    if any(kw in q for kw in dsa_keywords):
        return InvestigationPlan(
            intent="out_of_domain",
            required_sources=[],
            needs_clarification=False,
        )

    # General SRE code/script requests
    if "python code" in q or "provide code" in q or "write a script" in q or "sample code" in q:
        return InvestigationPlan(
            intent="general_sre_inquiry",
            required_sources=[],
            needs_clarification=False,
        )

    # Out of domain check (completely external topics)
    out_of_domain_keywords = [
        "recipe", "cook", "capital of", "weather in", "joke", "movie", "song", "lyrics",
        "football", "cricket", "basketball", "who won", "president of", "capital city",
        "tell me a story", "write a poem", "horoscope"
    ]
    if any(kw in q for kw in out_of_domain_keywords):
        return InvestigationPlan(
            intent="out_of_domain",
            required_sources=[],
            needs_clarification=False,
        )

    # Greeting / General conversation check
    greeting_keywords = ["hello", "hi", "hey", "who are you", "what can you do", "help me"]
    if q in greeting_keywords or any(q.startswith(g) and len(q) < 25 for g in greeting_keywords):
        return InvestigationPlan(
            intent="general_sre_inquiry",
            required_sources=[],
            needs_clarification=False,
        )

    # Vague question check
    if "deployment fail yesterday" in q or "what failed yesterday" in q or (q.startswith("what failed") and len(q) < 30):
        return InvestigationPlan(
            intent="clarification_needed",
            needs_clarification=True,
            clarification_question="Multiple incidents may have occurred. Could you specify which service, incident ID, or time window you would like to investigate?",
            required_sources=["incidents"],
        )

    # Historical RAG / follow-up
    historical_keywords = [
        "similar redis problem", "similar problem", "have we encountered", "have we experienced",
        "before", "previous", "historically", "happened before", "seen before", "prior incident",
        "postmortem", "runbook"
    ]
    if any(kw in q for kw in historical_keywords):
        return InvestigationPlan(
            intent="historical_rag",
            service_id=prior_service_id,
            incident_id=prior_incident_id,
            required_sources=["runbooks", "postmortems", "knowledge", "communications"],
            needs_clarification=False,
        )

    # Dynamic entity extraction
    # 1. Incident ID pattern (e.g. INC-2026-10-28-001, INC-1234)
    inc_match = re.search(r'\b(INC-[0-9A-Za-z-]+)\b', last_query, re.IGNORECASE)
    incident_id = inc_match.group(1).upper() if inc_match else prior_incident_id

    # 2. Service ID extraction
    # Look for kebab-case tokens or tokens containing service/api/cluster/gateway
    service_id = None
    svc_tokens = re.findall(r'\b([a-z0-9]+(?:-[a-z0-9]+)*(?:-service|-api|-engine|-gateway|-cluster|-db))\b', q)
    if svc_tokens:
        service_id = svc_tokens[0]
    elif "checkout" in q:
        service_id = "checkout-api"
    elif "auth" in q:
        service_id = "auth-service"
    elif "redis" in q:
        service_id = "redis-cluster-east"
    elif "payment" in q:
        service_id = "payment-service"
    elif "notification" in q:
        service_id = "notification-service"
    elif "billing" in q:
        service_id = "billing-service"
    else:
        service_id = prior_service_id

    # 3. Customer ID extraction
    customer_id = None
    if "acme" in q:
        customer_id = "acme-corp"
    elif "globex" in q:
        customer_id = "globex-corp"

    # 4. Dynamic Time range extraction (extracts ISO timestamps or date tokens dynamically)
    time_range = None
    iso_matches = re.findall(r'\b\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?\b', last_query)
    if len(iso_matches) >= 2:
        time_range = {"start": iso_matches[0], "end": iso_matches[1]}
    elif len(iso_matches) == 1:
        time_range = {"start": iso_matches[0], "end": iso_matches[0]}

    sources = ["topology", "deployments", "telemetry", "communications"]
    if customer_id or "sla" in q or "compensation" in q or "penalty" in q or "credit" in q:
        sources.append("sla")

    return InvestigationPlan(
        intent="incident_investigation" if (service_id or incident_id) else "follow_up_question" if prior_service_id else "incident_investigation",
        service_id=service_id,
        incident_id=incident_id,
        customer_id=customer_id,
        time_range=time_range,
        required_sources=sources,
        needs_clarification=False,
    )


def _extract_prior_context(messages: list) -> tuple[str | None, str | None]:
    """Extract previously established incident_id and service_id from message history dynamically."""
    inc_pattern = re.compile(r'\b(INC-[0-9A-Za-z-]+)\b', re.IGNORECASE)
    svc_pattern = re.compile(r'\b([a-z0-9]+(?:-[a-z0-9]+)*(?:-service|-api|-engine|-gateway|-cluster|-db))\b', re.IGNORECASE)

    found_inc = None
    found_svc = None

    for m in reversed(messages):
        content = m.content if isinstance(m.content, str) else str(m.content)
        if not found_inc:
            inc_match = inc_pattern.search(content)
            if inc_match:
                found_inc = inc_match.group(1).upper()
        if not found_svc:
            svc_match = svc_pattern.search(content)
            if svc_match:
                found_svc = svc_match.group(1).lower()
        if found_inc and found_svc:
            break

    return found_inc, found_svc


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

    # ── PRE-LLM DETERMINISTIC OVERRIDE ──────────────────────────────────────
    # For conversation-memory and out-of-domain intents, skip the LLM planner
    # entirely to avoid contamination from prior incident context in the thread.
    q_lower = last_user_msg.lower().strip()
    _memory_kws = [
        "what is my name", "what's my name", "who am i", "my name",
        "what did i ask", "what was the first", "what was my first",
        "what did i say", "previous question", "earlier question",
        "first code", "what was the code", "what code did i",
        "what was its response", "what was the response",
        "summarize our conversation", "what have we talked about",
    ]
    _dsa_kws = [
        "3 sum", "3sum", "two sum", "2sum", "leetcode", "dsa", "data structure",
        "binary search tree", "bst", "bubble sort", "quick sort", "quicksort", "merge sort",
        "mergesort", "insertion sort", "linked list", "binary tree", "trie", "knapsack",
        "dynamic programming", "tower of hanoi", "fibonacci", "palindrome", "prime number",
        "invert a binary tree", "matrix multiplication", "depth first search", "breadth first search",
        "dijkstra", "topological sort", "graph coloring", "competitive programming"
    ]
    _ood_kws = [
        "recipe", "cook", "capital of", "weather in", " joke", "movie", "song", "lyrics",
        "football", "cricket", "basketball", "who won", "president of", "capital city",
        "tell me a story", "write a poem", "horoscope", "politics", "minister"
    ]
    if any(kw in q_lower for kw in _dsa_kws):
        plan = InvestigationPlan(intent="out_of_domain", required_sources=[], needs_clarification=False)
    elif any(kw in q_lower for kw in _memory_kws):
        plan = InvestigationPlan(intent="conversation_memory", required_sources=[], needs_clarification=False)
    elif any(kw in q_lower for kw in _ood_kws):
        plan = InvestigationPlan(intent="out_of_domain", required_sources=[], needs_clarification=False)
    # ── END PRE-LLM OVERRIDE ─────────────────────────────────────────────────

    llm = get_llm(temperature=0.0)
    if llm and plan is None:
        try:
            structured_llm = llm.with_structured_output(InvestigationPlan, method="function_calling")

            # Build conversation context for planner
            planner_msgs = [SystemMessage(content=PLANNER_PROMPT)]
            recent = messages[-6:] if len(messages) > 6 else messages
            for m in recent:
                role = getattr(m, "type", None) or getattr(m, "role", None)
                content = m.content if isinstance(m.content, str) else str(m.content)
                if role in ("human", "user") and content != last_user_msg:
                    planner_msgs.append(HumanMessage(content=f"[Previous query]: {content}"))
                elif role in ("ai", "assistant"):
                    summary = content[:300] + "..." if len(content) > 300 else content
                    planner_msgs.append(AIMessage(content=f"[Previous response summary]: {summary}"))

            context_hint = ""
            if prior_incident_id or prior_service_id:
                context_hint = f"\n[Context: Previous investigation touched incident={prior_incident_id}, service={prior_service_id}. If this is a follow-up, preserve that context.]"

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
