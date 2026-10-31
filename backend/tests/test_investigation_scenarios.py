"""Comprehensive validation of the 10 core investigation scenarios required by Section 16."""

import uuid
from app.graph.planner import plan_investigation
from app.graph.verifier import verify_evidence
from app.graph.report_generator import generate_report
from app.services.sla_service import calculate_sla_assessment
from app.services.evidence_service import EvidenceService
from app.schemas.investigation import (
    EvidenceItem,
    EvidenceClassification,
    SLAStatus,
    InvestigationStatus,
    RootCauseStatus,
)
from langchain_core.messages import HumanMessage


def test_scenario_1_main_root_cause_investigation():
    """Test 1: Checkout API 504 errors on Oct 28 & Acme Corp SLA assessment."""
    contract_data = {
        "customer_id": "acme-corp",
        "contract_name": "Master Enterprise Agreement 2026",
        "credit_tiers": [
            {"min_downtime_minutes": 0, "max_downtime_minutes": 19, "credit_percent": 0.0, "rca_required": False},
            {"min_downtime_minutes": 20, "max_downtime_minutes": 30, "credit_percent": 0.0, "rca_required": True},
            {"min_downtime_minutes": 31, "max_downtime_minutes": 60, "credit_percent": 5.0, "rca_required": True},
        ],
    }

    # 23 minutes of downtime
    sla = calculate_sla_assessment(contract_data, downtime_minutes=23, customer_id="acme-corp")
    assert sla.status == SLAStatus.ASSESSED
    assert sla.rca_required is True
    assert sla.credit_percent == 0.0


def test_scenario_2_conflict_detection():
    """Test 2: Contradiction detection between Slack DDoS speculation and telemetry baseline."""
    ev1 = EvidenceItem(
        evidence_id="EVD-001",
        source_type="slack_message",
        source_id="MSG-001",
        title="Slack speculation",
        content="External DDoS attack suspected",
        classification=EvidenceClassification.UNVERIFIED,
    )
    ev2 = EvidenceItem(
        evidence_id="EVD-002",
        source_type="telemetry",
        source_id="METRIC-001",
        title="Ingress traffic",
        content="Ingress RPS remained at 1210 baseline",
        classification=EvidenceClassification.CONTRADICTING,
    )
    contradictions = EvidenceService.classify_contradictions([ev1, ev2])
    assert len(contradictions) == 1
    assert contradictions[0].source_id == "METRIC-001"


def test_scenario_3_unanswerable_question():
    """Test 3: Refusal to speculate on unencrypted PII exposure without DLP/audit evidence."""
    state = {
        "messages": [HumanMessage(content="Did the EU cluster memory leak expose unencrypted customer PII?")],
        "investigation_plan": {
            "intent": "incident_investigation",
            "service_id": "auth-service",
            "incident_id": "INC-2026-10-15-002",
        },
        "evidence_items": [
            {
                "evidence_id": "EVD-001",
                "source_type": "telemetry",
                "source_id": "METRIC-OOM",
                "title": "Pod OOMKilled",
                "content": "Pod memory exceeded limit",
            }
        ],
        "verification_feedback": None,
        "verification_attempts": 0,
        "tool_iterations": 1,
        "investigation_result": None,
        "investigation_status": "in_progress",
        "run_id": "test_run",
        "thread_id": "test_thread",
    }
    ver_res = verify_evidence(state)
    assert ver_res["verification_feedback"] is not None
    assert "DLP" in ver_res["verification_feedback"] or "audit" in ver_res["verification_feedback"].lower()

    state.update(ver_res)
    rep_res = generate_report(state)
    report = rep_res["investigation_result"]
    assert report["investigation_status"] == InvestigationStatus.INSUFFICIENT_EVIDENCE
    assert report["root_cause"]["status"] == RootCauseStatus.UNKNOWN
    assert len(report["missing_evidence"]) > 0


def test_scenario_4_vague_question():
    """Test 4: Vague question asks user for clarification instead of guessing."""
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
    plan_res = plan_investigation(state)
    assert plan_res["investigation_plan"]["needs_clarification"] is True
    assert plan_res["investigation_plan"]["clarification_question"] is not None


def test_scenario_5_historical_rag():
    """Test 5: Historical incident and runbook retrieval."""
    state = {
        "messages": [HumanMessage(content="Have we encountered a similar Redis problem before? How did we fix it?")],
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
    plan_res = plan_investigation(state)
    assert plan_res["investigation_plan"]["intent"] == "historical_rag"
    assert "runbooks" in plan_res["investigation_plan"]["required_sources"]


def test_scenario_8_thread_isolation():
    """Test 8: Thread isolation ensures separate conversations do not leak context."""
    from app.services.thread_service import thread_service
    from app.services.chat_service import chat_service

    t1 = thread_service.create_thread(title="Thread 1: Checkout Outage")
    t2 = thread_service.create_thread(title="Thread 2: Billing Latency")

    chat_service.record_user_message(thread_id=t1["thread_id"], content="Checkout issue")
    chat_service.record_user_message(thread_id=t2["thread_id"], content="Billing issue")

    msgs1 = chat_service.get_messages(thread_id=t1["thread_id"])
    msgs2 = chat_service.get_messages(thread_id=t2["thread_id"])

    assert all(m["content"] != "Billing issue" for m in msgs1)
    assert all(m["content"] != "Checkout issue" for m in msgs2)

    # Cleanup
    thread_service.delete_thread(t1["thread_id"])
    thread_service.delete_thread(t2["thread_id"])


def test_scenario_10_citation_validation():
    """Test 10: Citation validation rejects nonexistent citations."""
    collected_evidence = [
        EvidenceItem(
            evidence_id="EVD-001",
            source_type="deployment_pr",
            source_id="PR-812",
            title="PR #812 Diff",
            content="Pool reduced from 500 to 50",
        )
    ]

    report_citations = [
        {"evidence_id": "EVD-001", "source_id": "PR-812"},
        {"evidence_id": "EVD-999-FAKE", "source_id": "PR-FAKE-999"},  # Invalid
    ]

    validated = EvidenceService.validate_citations(report_citations, collected_evidence)
    assert len(validated) == 1
    assert validated[0]["evidence_id"] == "EVD-001"

