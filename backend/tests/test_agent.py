"""Unit tests for LangGraph Agent StateGraph and nodes."""

from app.graph.builder import build_graph
from app.graph.state import AgentState
from app.graph.planner import plan_investigation, InvestigationPlan
from app.graph.verifier import verify_evidence, EvidenceReview
from app.graph.report_generator import generate_report
from app.graph.routing import route_after_planner, route_after_agent, route_after_verifier
from langchain_core.messages import HumanMessage, AIMessage


def test_agent_graph_compilation():
    """Verify LangGraph compiles without errors."""
    graph = build_graph()
    assert graph is not None


def test_planner_node_heuristics():
    """Verify planner identifies key entities and vagueness."""
    # Vague question
    state = {
        "messages": [HumanMessage(content="Why did the deployment fail yesterday?")],
        "investigation_plan": {},
        "evidence_items": [],
        "verification_feedback": None,
        "verification_attempts": 0,
        "tool_iterations": 0,
        "investigation_result": None,
        "investigation_status": "in_progress",
        "run_id": "test_run",
        "thread_id": "test_thread",
    }
    res = plan_investigation(state)
    assert res["investigation_plan"]["needs_clarification"] is True
    assert route_after_planner(res) == "report_generator"

    # Specific question
    state["messages"] = [
        HumanMessage(content="Why did Checkout API fail on October 28 between 14:00 and 14:25 UTC?")
    ]
    res2 = plan_investigation(state)
    assert res2["investigation_plan"]["needs_clarification"] is False
    assert res2["investigation_plan"]["service_id"] == "checkout-api"
    assert route_after_planner(res2) == "agent"


def test_verifier_node():
    """Verify verifier checks evidence sufficiency and loops accordingly."""
    state = {
        "messages": [],
        "investigation_plan": {"service_id": "checkout-api", "incident_id": "INC-2026-10-28-001"},
        "evidence_items": [
            {
                "evidence_id": "EVD-001",
                "source_type": "deployment_pr",
                "source_id": "PR-812",
                "title": "Config change",
                "content": "PR-812 reduced Redis pool",
            },
            {
                "evidence_id": "EVD-002",
                "source_type": "telemetry",
                "source_id": "METRIC-001",
                "title": "Redis pool saturation",
                "content": "Redis pool utilization reached 100%",
            },
        ],
        "verification_feedback": None,
        "verification_attempts": 0,
        "tool_iterations": 1,
        "investigation_result": None,
        "investigation_status": "in_progress",
        "run_id": "test_run",
        "thread_id": "test_thread",
    }
    res = verify_evidence(state)
    # Evidence is sufficient so verification feedback should be None
    assert res["verification_feedback"] is None
    state.update(res)
    assert route_after_verifier(state) == "report_generator"


def test_report_generator_schema_conformance():
    """Verify report generator produces valid InvestigationReport schema."""
    state = {
        "messages": [],
        "investigation_plan": {
            "service_id": "checkout-api",
            "incident_id": "INC-2026-10-28-001",
            "customer_id": "acme-corp",
        },
        "evidence_items": [
            {
                "evidence_id": "EVD-001",
                "source_type": "deployment_pr",
                "source_id": "PR-812",
                "title": "PR-812 Redis pool reduction",
                "content": "Pool reduced 500 to 50",
                "classification": "supporting",
            }
        ],
        "verification_feedback": None,
        "verification_attempts": 1,
        "tool_iterations": 1,
        "investigation_result": None,
        "investigation_status": "in_progress",
        "run_id": "test_run",
        "thread_id": "test_thread",
    }
    res = generate_report(state)
    report = res["investigation_result"]
    assert report is not None
    assert report["investigation_status"] == "completed"
    assert report["root_cause"] is not None
    assert len(report["recommendations"]) > 0


def test_out_of_domain_and_greeting_zero_tools():
    """Verify out-of-domain and greeting queries produce zero tool calls and complete cleanly."""
    from app.graph.nodes import agent_node

    # 1. Out of domain query
    ood_state = {
        "messages": [HumanMessage(content="What is the capital of France?")],
        "investigation_plan": {},
        "evidence_items": [],
        "tool_iterations": 0,
        "run_id": "test_ood",
        "thread_id": "test_ood",
    }
    plan_res = plan_investigation(ood_state)
    assert plan_res["investigation_plan"]["intent"] == "out_of_domain"
    ood_state["investigation_plan"] = plan_res["investigation_plan"]

    # Agent node should make zero tool calls
    agent_res = agent_node(ood_state)
    last_msg = agent_res["messages"][-1]
    assert not getattr(last_msg, "tool_calls", None)
    assert "AegisRCA" in str(last_msg.content)
    ood_state["messages"].append(last_msg)

    # Route after agent should go directly to verifier
    assert route_after_agent(ood_state) == "verifier"

    # Route after verifier should proceed to report_generator without looping
    assert route_after_verifier(ood_state) == "report_generator"

    # Report generator should record completed status with the agent's refusal response
    rep_res = generate_report(ood_state)
    assert rep_res["investigation_status"] == "completed"
    assert "AegisRCA" in rep_res["investigation_result"]["summary"]


def test_insufficient_evidence_when_no_data():
    """Verify that when tools find zero evidence for an incident, the agent reports insufficient evidence and next steps."""
    empty_ev_state = {
        "messages": [HumanMessage(content="Why did payment-service fail at 10:00 UTC?")],
        "investigation_plan": {
            "intent": "incident_investigation",
            "service_id": "payment-service",
            "incident_id": None,
        },
        "evidence_items": [],
        "tool_iterations": 1,
        "verification_attempts": 1,
        "run_id": "test_empty_ev",
        "thread_id": "test_empty_ev",
    }
    rep_res = generate_report(empty_ev_state)
    assert rep_res["investigation_status"] == "insufficient_evidence"
    result = rep_res["investigation_result"]
    assert "cannot be answered from the available context" in result["summary"].lower()
    assert "not sure" in result["summary"].lower() or "insufficient" in result["summary"].lower()
    assert result["root_cause"]["status"] == "unknown"
    assert len(result["missing_evidence"]) > 0
    assert len(result["recommendations"]) > 0


def test_dsa_query_hardrailing_refusal():
    """Verify DSA, LeetCode, and competitive programming queries are strictly rejected as out-of-domain."""
    from app.graph.nodes import agent_node

    dsa_state = {
        "messages": [HumanMessage(content="can you provide me python code for 3 sum problem?")],
        "investigation_plan": {},
        "evidence_items": [],
        "tool_iterations": 0,
        "run_id": "test_dsa",
        "thread_id": "test_dsa",
    }
    plan_res = plan_investigation(dsa_state)
    assert plan_res["investigation_plan"]["intent"] == "out_of_domain"
    dsa_state["investigation_plan"] = plan_res["investigation_plan"]

    agent_res = agent_node(dsa_state)
    last_msg = agent_res["messages"][-1]
    # Must not invoke any tools
    assert not getattr(last_msg, "tool_calls", None)
    # Must refuse DSA specifically
    assert "data structures & algorithms" in str(last_msg.content).lower() or "leetcode" in str(last_msg.content).lower() or "dsa" in str(last_msg.content).lower()
    assert "production" in str(last_msg.content).lower() or "sre" in str(last_msg.content).lower()

