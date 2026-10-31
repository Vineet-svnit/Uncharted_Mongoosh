"""Investigation Retrieval Tools for LangGraph Agent.

Exposes 9 standard LangChain-compatible tools wrapping the underlying data layer.
All tools return JSON strings to maintain deterministic agent tool contracts.
"""

from typing import Any
import json
import logging
from langchain_core.tools import tool

from app.services.data_layer_adapter import adapter
from app.services.sla_service import calculate_sla_assessment

logger = logging.getLogger(__name__)


@tool
def list_known_incidents(date: str | None = None, status: str | None = None) -> str:
    """List recorded production incidents, optionally filtered by ISO-8601 date or status.

    Args:
        date: Filter incidents starting on this date (e.g. '2026-10-28').
        status: Filter by status ('open', 'resolved', 'postmortem').
    """
    try:
        incidents = adapter.list_known_incidents(date=date, status=status)
        return json.dumps({"status": "success", "count": len(incidents), "incidents": incidents})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "incidents": []})


@tool
def get_incident_details(incident_id: str) -> str:
    """Retrieve full details of a specific incident including affected service, time window, customer, and severity.

    Args:
        incident_id: Unique incident identifier, e.g. 'INC-2026-10-28-001'.
    """
    try:
        inc = adapter.get_incident_details(incident_id=incident_id)
        if not inc:
            return json.dumps({"status": "not_found", "incident_id": incident_id})
        return json.dumps({"status": "success", "incident": inc})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def trace_service_dependencies(
    service_id: str,
    environment: str = "production",
    topology_version: str = "prod-2026-10-28",
) -> str:
    """Trace upstream and downstream microservice dependencies and failure chains for a service.

    Args:
        service_id: Root service ID to trace (e.g. 'checkout-api', 'auth-service').
        environment: Topology environment (default: 'production').
        topology_version: Snapshot tag (default: 'prod-2026-10-28').
    """
    try:
        chain = adapter.trace_service_dependencies(
            service_id=service_id,
            environment=environment,
            topology_version=topology_version,
        )
        return json.dumps({"status": "success", "topology": chain})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def find_recent_deployments(
    service_id: str,
    start: str | None = None,
    end: str | None = None,
) -> str:
    """Find CI/CD deployments and GitHub PR merges that occurred around an incident time window.

    Args:
        service_id: Service ID to check deployments for (e.g. 'auth-service', 'checkout-api').
        start: Start of time window in ISO-8601 (e.g. '2026-10-28T13:30:00Z').
        end: End of time window in ISO-8601 (e.g. '2026-10-28T14:30:00Z').
    """
    try:
        evidence = adapter.find_recent_deployments(
            service_id=service_id, start=start, end=end
        )
        items = [e.model_dump(mode="json") for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "deployments": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "deployments": []})


@tool
def search_engineering_knowledge(
    query: str,
    source_type: str | None = None,
    service_id: str | None = None,
    incident_id: str | None = None,
    customer_id: str | None = None,
    limit: int = 5,
) -> str:
    """Semantic and keyword search over runbooks, postmortems, architecture RFCs, and SLA documentation.

    Args:
        query: Technical search text (e.g. 'Redis connection pool exhaustion', 'runbook auth-service').
        source_type: Optional filter: 'runbook', 'postmortem', 'architecture_rfc', 'sla_text'.
        service_id: Optional service filter.
        incident_id: Optional incident filter.
        customer_id: Optional customer filter.
        limit: Max results to return (default: 5).
    """
    try:
        evidence = adapter.search_engineering_knowledge(
            query=query,
            source_type=source_type,
            service_id=service_id,
            incident_id=incident_id,
            customer_id=customer_id,
            limit=limit,
        )
        items = [e.model_dump(mode="json") for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "knowledge_items": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "knowledge_items": []})


@tool
def query_service_telemetry(
    service_id: str,
    start: str,
    end: str,
) -> str:
    """Retrieve telemetry metrics and error logs for a service during a specific incident window.

    Args:
        service_id: Service ID (e.g. 'checkout-api', 'auth-service', 'redis-cluster-east').
        start: Start timestamp in ISO-8601 (e.g. '2026-10-28T14:00:00Z').
        end: End timestamp in ISO-8601 (e.g. '2026-10-28T14:25:00Z').
    """
    try:
        evidence = adapter.query_service_telemetry(
            service_id=service_id, start=start, end=end
        )
        items = [e.model_dump(mode="json") for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "telemetry": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "telemetry": []})


@tool
def search_incident_messages(
    query: str,
    incident_id: str | None = None,
    limit: int = 10,
) -> str:
    """Search Slack war room communications and engineer discussions for incident context.

    Args:
        query: Discussion query (e.g. 'Redis pool', '504', 'DDoS rumors').
        incident_id: Optional incident ID filter.
        limit: Max messages to return (default: 10).
    """
    try:
        evidence = adapter.search_incident_messages(
            query=query, incident_id=incident_id, limit=limit
        )
        items = [e.model_dump(mode="json") for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "messages": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "messages": []})


@tool
def retrieve_customer_sla(customer_id: str) -> str:
    """Retrieve contractual SLA terms and calculate penalty/remedy obligations using deterministic business logic.

    Args:
        customer_id: Customer identifier, e.g. 'acme-corp'.
    """
    try:
        contract_data = adapter.retrieve_customer_sla(customer_id=customer_id)
        if not contract_data:
            return json.dumps(
                {
                    "status": "not_found",
                    "customer_id": customer_id,
                    "message": f"No SLA contract found for customer '{customer_id}'.",
                }
            )

        downtime_minutes = 23
        assessment = calculate_sla_assessment(
            contract_data=contract_data,
            downtime_minutes=downtime_minutes,
            customer_id=customer_id,
        )

        return json.dumps(
            {
                "status": "success",
                "customer_id": customer_id,
                "contract_name": contract_data.get("contract_name"),
                "assessment": assessment.model_dump(mode="json"),
                "pdf_file_id": contract_data.get("pdf_file_id"),
                "file_name": contract_data.get("file_name"),
                "clauses": contract_data.get("clauses", []),
            }
        )
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def search_visual_evidence(
    query: str,
    incident_id: str | None = None,
    limit: int = 3,
) -> str:
    """Retrieve visual monitoring evidence such as Grafana dashboard screenshots.

    Args:
        query: Visual search query ('Redis connection pool saturation', '504 spike chart').
        incident_id: Optional incident identifier.
        limit: Max visual items (default 3).
    """
    try:
        evidence = adapter.search_visual_evidence(query=query, incident_id=incident_id, limit=limit)
        items = [e.model_dump(mode="json") for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "visual_evidence": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e), "visual_evidence": []})


ALL_INVESTIGATION_TOOLS = [
    list_known_incidents,
    get_incident_details,
    trace_service_dependencies,
    find_recent_deployments,
    search_engineering_knowledge,
    query_service_telemetry,
    search_incident_messages,
    retrieve_customer_sla,
    search_visual_evidence,
]
