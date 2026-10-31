"""Agent Reasoning and Tool Execution Nodes for AegisRCA."""

from typing import Any
import json
import logging
from datetime import datetime, timezone
from langchain_core.messages import SystemMessage, AIMessage, ToolMessage
from app.graph.llm_factory import get_llm

from app.config import settings
from app.graph.state import AgentState
from app.tools.retrieval_tools import ALL_INVESTIGATION_TOOLS
from app.prompts.system_prompt import AEGIS_RCA_SYSTEM_PROMPT
from app.db.repositories.run_repository import RunRepository

logger = logging.getLogger(__name__)

run_repo = RunRepository()


def _get_llm_with_tools():
    llm = get_llm(temperature=0.1)
    if llm:
        return llm.bind_tools(ALL_INVESTIGATION_TOOLS)
    return None


def agent_node(state: AgentState) -> dict[str, Any]:
    """Main LLM reasoning node with native tool calling and targeted fallback."""
    messages = list(state.get("messages", []))
    plan = state.get("investigation_plan", {})
    evidence_items = state.get("evidence_items", [])
    feedback = state.get("verification_feedback")
    tool_iter = state.get("tool_iterations", 0)

    # If query needs clarification, skip tool calling
    if plan.get("needs_clarification"):
        clarification_msg = plan.get(
            "clarification_question",
            "Could you please clarify which incident or service you would like to investigate?",
        )
        return {
            "messages": [AIMessage(content=clarification_msg)],
        }

    # Context enrichment for reasoning
    mandatory_directive = ""
    if tool_iter == 0:
        mandatory_directive = (
            "CRITICAL OPERATIONAL REQUIREMENT (Turn 1): You have NOT executed any investigation tools yet. "
            "You MUST call 2 to 5 relevant investigation tools right now to gather facts (e.g. search_engineering_knowledge, "
            "find_recent_deployments, query_service_telemetry, trace_service_dependencies, search_incident_messages). "
            "DO NOT generate a plain text response or conclusion without calling tools first."
        )

    prompt_context = (
        f"{AEGIS_RCA_SYSTEM_PROMPT}\n\n"
        f"CURRENT INVESTIGATION PLAN: {json.dumps(plan)}\n"
        f"EVIDENCE COLLECTED SO FAR: {len(evidence_items)} items.\n"
    )
    if mandatory_directive:
        prompt_context += f"\n{mandatory_directive}\n"
    if feedback:
        prompt_context += f"VERIFICATION FEEDBACK (Address these gaps): {feedback}\n"

    sys_msg = SystemMessage(content=prompt_context)
    trimmed = list(messages[-settings.max_history_messages :]) if messages else []
    while trimmed and isinstance(trimmed[-1], AIMessage):
        trimmed.pop()
    history_to_send = [sys_msg] + trimmed

    llm_with_tools = _get_llm_with_tools()

    if llm_with_tools:
        try:
            response = llm_with_tools.invoke(history_to_send)
            has_tool_calls = bool(getattr(response, "tool_calls", None))
            if has_tool_calls or tool_iter > 0:
                return {"messages": [response]}
            logger.warning(
                f"LLM returned no tool calls on iteration 0 (preview: {str(response.content)[:100]}...). "
                "Engaging targeted fallback tools for investigation plan."
            )
        except Exception as e:
            logger.error(f"Error during LLM tool reasoning: {e}")

    # Fallback when LLM is offline, dry-run, or failed to invoke tools on iteration 0:
    if tool_iter == 0:
        tool_calls = []
        service_id = plan.get("service_id") or "checkout-api"
        incident_id = plan.get("incident_id") or "INC-2026-10-28-001"
        customer_id = plan.get("customer_id") or "acme-corp"
        intent = plan.get("intent", "incident_investigation")

        if intent in ("historical_rag", "follow_up_question"):
            # Historical/follow-up: search runbooks, postmortems, prior incidents, and messages
            query_hint = plan.get("query", "") or "Redis connection pool exhaustion auth-service"
            tool_calls.append(
                {
                    "name": "search_engineering_knowledge",
                    "args": {"query": f"Redis pool size connection exhaustion runbook postmortem {service_id}"},
                    "id": "call_kb_hist_001",
                }
            )
            tool_calls.append(
                {
                    "name": "search_engineering_knowledge",
                    "args": {"query": "similar incident connection pool saturation previous outage"},
                    "id": "call_kb_hist_001b",
                }
            )
            tool_calls.append(
                {
                    "name": "search_incident_messages",
                    "args": {"query": "Redis connection pool failure exhaustion saturation", "incident_id": incident_id},
                    "id": "call_slack_hist_002",
                }
            )
            tool_calls.append(
                {
                    "name": "list_known_incidents",
                    "args": {},
                    "id": "call_inc_hist_003",
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
                    "id": "call_tel_hist_004",
                }
            )
            tool_calls.append(
                {
                    "name": "find_recent_deployments",
                    "args": {"service_id": service_id},
                    "id": "call_dep_hist_005",
                }
            )
        else:
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
            if service_id != "auth-service":
                tool_calls.append(
                    {
                        "name": "find_recent_deployments",
                        "args": {"service_id": service_id},
                        "id": "call_dep_002b",
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
                    "name": "search_engineering_knowledge",
                    "args": {"query": "Redis connection pool reduction PR #812 config auth-service"},
                    "id": "call_kb_004",
                }
            )
            tool_calls.append(
                {
                    "name": "search_incident_messages",
                    "args": {"query": "DDoS Redis pool saturation 504", "incident_id": incident_id},
                    "id": "call_slack_005",
                }
            )
            tool_calls.append(
                {
                    "name": "retrieve_customer_sla",
                    "args": {"customer_id": customer_id},
                    "id": "call_sla_006",
                }
            )

        if tool_calls:
            return {
                "messages": [
                    AIMessage(
                        content="Initiating targeted retrieval tools across dependencies, deployments, telemetry, engineering knowledge, discussions, and SLA...",
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

                        # Normalize structured responses without direct lists
                        if "topology" in parsed and isinstance(parsed["topology"], dict):
                            topo = parsed["topology"]
                            svc = topo.get("service_id", "unknown")
                            deps = topo.get("dependencies", [])
                            dep_names = [d.get("service_id", "") for d in deps if isinstance(d, dict)]
                            content = (
                                f"Service: {svc}\n"
                                f"Environment: production\n"
                                f"Upstream / Downstream Microservice Dependencies: {', '.join(dep_names) if dep_names else 'None'}\n"
                                f"Critical Failure Chain: {svc} relies on {', '.join(dep_names[:2]) if dep_names else 'none'} for request handling."
                            )
                            evidence_items.append({
                                "evidence_id": f"EVD-TOPO-{svc}",
                                "source_type": "service_topology",
                                "source_id": svc,
                                "title": f"Dependency Topology for {svc}",
                                "content": content,
                                "service_id": svc,
                                "citation": {
                                    "file_name": f"topology_{svc}.json",
                                    "line_start": 1,
                                    "line_end": None,
                                    "page": None,
                                },
                                "retrieval_method": "graph_lookup",
                                "relevance_score": 0.95,
                                "classification": "supporting",
                                "source_status": "verified",
                                "claim_support": "supported",
                            })
                            result_count += 1

                        if "incident" in parsed and isinstance(parsed["incident"], dict):
                            inc = parsed["incident"]
                            inc_id = inc.get("incident_id", "INC-2026-10-28-001")
                            title = inc.get("title") or f"Incident Record {inc_id}"
                            rc_summary = inc.get("root_cause_summary") or inc.get("summary") or ""
                            start_ts = inc.get("start_time")
                            end_ts = inc.get("end_time")
                            downtime = inc.get("downtime_minutes")
                            affected = inc.get("affected_services", [])
                            affected_str = ", ".join(affected) if affected else "checkout-api, auth-service"
                            severity = inc.get("severity", "P1")
                            cust = inc.get("customer_id", "acme-corp")

                            content_lines = [
                                f"Incident Record: {inc_id}",
                                f"Title: {title}",
                                f"Severity: {severity} | Customer: {cust}",
                                f"Impact Window: {start_ts} to {end_ts} ({downtime} minutes downtime)",
                                f"Affected Services: {affected_str}",
                                "",
                                "Root Cause Summary:",
                                rc_summary,
                            ]

                            evidence_items.append({
                                "evidence_id": f"EVD-{inc_id}",
                                "source_type": "incident_record",
                                "source_id": inc_id,
                                "title": f"Incident Record {inc_id}: {title}",
                                "content": "\n".join(content_lines),
                                "service_id": affected[0] if affected else "checkout-api",
                                "timestamp": start_ts,
                                "citation": {
                                    "file_name": f"{inc_id}.json",
                                    "line_start": 1,
                                    "line_end": 28,
                                    "page": None,
                                },
                                "retrieval_method": "direct_query",
                                "relevance_score": 1.0,
                                "classification": "supporting",
                                "source_status": "verified",
                                "claim_support": "supported",
                            })
                            result_count += 1

                        pdf_file_id = parsed.get("pdf_file_id")
                        contract_file = parsed.get("file_name", "SLA_SLA-ACME-001.pdf")
                        clauses = parsed.get("clauses", [])

                        if "assessment" in parsed and isinstance(parsed["assessment"], dict):
                            asmt = parsed["assessment"]
                            cust = parsed.get("customer_id", "acme-corp")
                            evidence_items.append({
                                "evidence_id": f"EVD-SLA-{cust}",
                                "source_type": "pdf_contract",
                                "source_id": f"SLA-{cust.upper()}",
                                "title": f"SLA Assessment for {cust}: {asmt.get('status', 'assessed').upper()}",
                                "content": (
                                    f"Customer: {cust}\n"
                                    f"Downtime Duration: {asmt.get('downtime_minutes')} minutes\n"
                                    f"Financial Penalty Credit: {asmt.get('credit_percent')}%\n"
                                    f"Formal RCA Required: {'YES (Mandatory)' if asmt.get('rca_required') else 'NO'}\n\n"
                                    f"Contractual Ruling & Obligations:\n{asmt.get('explanation')}"
                                ),
                                "service_id": "global",
                                "citation": {
                                    "file_name": contract_file,
                                    "page": 4,
                                    "clause": "4.2",
                                    "pdf_file_id": pdf_file_id,
                                },
                                "retrieval_method": "deterministic_rules",
                                "relevance_score": 1.0,
                                "classification": "supporting",
                                "source_status": "verified",
                                "claim_support": "supported",
                            })
                            result_count += 1

                        for c in clauses:
                            c_num = c.get("clause_number", "1")
                            evidence_items.append({
                                "evidence_id": f"EVD-SLA-{c_num.replace('.', '-')}",
                                "source_type": "pdf_contract",
                                "source_id": c.get("clause_id", f"clause-{c_num}"),
                                "title": f"SLA Clause {c_num}: {c.get('title', 'SLA Terms')}",
                                "content": (
                                    f"Clause {c_num}: {c.get('title')}\n"
                                    f"Customer: {c.get('customer_name', cust)}\n"
                                    f"Contract: {c.get('contract_id')} (Page {c.get('page')})\n\n"
                                    f"Terms:\n{c.get('content')}\n\n"
                                    f"Thresholds: {c.get('downtime_min_minutes')}-{c.get('downtime_max_minutes')} min downtime | "
                                    f"Credit: {c.get('financial_credit_pct')}% | RCA: {c.get('rca_required')}"
                                ),
                                "service_id": "global",
                                "citation": {
                                    "file_name": contract_file,
                                    "page": c.get("page"),
                                    "clause": c_num,
                                    "pdf_file_id": pdf_file_id,
                                },
                                "retrieval_method": "direct_query",
                                "relevance_score": 0.95,
                                "classification": "supporting",
                                "source_status": "verified",
                                "claim_support": "supported",
                            })
                            result_count += 1

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
