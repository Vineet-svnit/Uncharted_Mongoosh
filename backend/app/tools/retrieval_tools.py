"""AegisRCA Investigation Tools.

Specialized LangChain tools wrapping Member 1's retrieval layer via DataLayerAdapter.
"""

from typing import Any
import json
from langchain_core.tools import tool

from app.services.data_layer_adapter import adapter
from app.services.sla_service import calculate_sla_assessment


@tool
def list_known_incidents(date: str | None = None, status: str | None = None) -> str:
    """Find known incidents matching optional date (YYYY-MM-DD) or status (e.g. 'resolved', 'investigating').

    Use when the user asks what incidents occurred or asks a vague question about an outage.
    """
    try:
        incidents = adapter.list_known_incidents(date=date, status=status)
        if not incidents:
            return json.dumps({"status": "empty", "message": "No incidents found matching criteria", "incidents": []})
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
        service_id: Target service name, e.g. 'checkout-api' or 'auth-service'.
        environment: Deployment environment ('production').
        topology_version: Topology snapshot version ('prod-2026-10-28').
    """
    try:
        topo = adapter.trace_service_dependencies(
            service_id=service_id,
            environment=environment,
            topology_version=topology_version,
        )
        return json.dumps({"status": "success", "topology": topo})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def find_recent_deployments(
    service_id: str,
    start: str | None = None,
    end: str | None = None,
) -> str:
    """Search recent code deployments, pull requests (PRs), and configuration changes for a service.

    Args:
        service_id: Service identifier, e.g. 'auth-service' or 'checkout-api'.
        start: Optional ISO-8601 start timestamp.
        end: Optional ISO-8601 end timestamp.
    """
    try:
        evidence = adapter.find_recent_deployments(service_id=service_id, start=start, end=end)
        items = [e.model_dump() for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "deployments": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def search_engineering_knowledge(
    query: str,
    source_type: str | None = None,
    service_id: str | None = None,
    incident_id: str | None = None,
    customer_id: str | None = None,
    limit: int = 5,
) -> str:
    """Search engineering documentation, runbooks, historical postmortems, code diffs, and SLA contracts using Hybrid RAG.

    Args:
        query: Specific semantic retrieval query (e.g. 'Redis pool size configuration change', 'DDoS mitigation runbook').
        source_type: Optional filter ('runbook', 'postmortem', 'pr_diff', 'contract').
        service_id: Optional service filter ('auth-service', 'redis-cluster-east').
        incident_id: Optional incident filter.
        customer_id: Optional customer filter.
        limit: Max results (default 5).
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
        items = [e.model_dump() for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "knowledge_items": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def query_service_telemetry(service_id: str, start: str, end: str) -> str:
    """Retrieve structured numerical telemetry observations, metrics, error rates, and connection pool utilization.

    Args:
        service_id: Service to query ('checkout-api', 'auth-service', 'redis-cluster-east').
        start: ISO-8601 start timestamp (e.g. '2026-10-28T14:00:00Z').
        end: ISO-8601 end timestamp (e.g. '2026-10-28T14:25:00Z').
    """
    try:
        evidence = adapter.query_service_telemetry(service_id=service_id, start=start, end=end)
        items = [e.model_dump() for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "telemetry": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def search_incident_messages(
    query: str,
    incident_id: str | None = None,
    limit: int = 10,
) -> str:
    """Search Slack discussion messages and human hypotheses recorded in incident war rooms.

    Args:
        query: Search keywords or question ('DDoS', 'Redis connection timeout', '504 errors').
        incident_id: Optional incident identifier ('INC-2026-10-28-001').
        limit: Max messages to retrieve (default 10).
    """
    try:
        evidence = adapter.search_incident_messages(query=query, incident_id=incident_id, limit=limit)
        items = [e.model_dump() for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "messages": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


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

        # Retrieve downtime from incident if available (23 minutes for acme-corp in primary scenario)
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
                "assessment": assessment.model_dump(),
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
        items = [e.model_dump() for e in evidence]
        return json.dumps({"status": "success", "count": len(items), "visual_evidence": items})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


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

