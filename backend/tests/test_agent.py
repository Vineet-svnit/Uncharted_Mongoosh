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

