"""
backend/data_layer/__init__.py
------------------------------
Public API for the AegisRCA data layer.

Member 2 usage:

    from data_layer import (
        get_dependency_chain,
        search_knowledge,
        query_telemetry,
        search_messages,
        search_sla,
        get_deployments,
        get_incident,
        list_incidents,
        search_visual_evidence,
        get_visual_asset,
    )
"""

from .retrieval import (
    get_dependency_chain,
    get_deployments,
    get_incident,
    get_visual_asset,
    list_incidents,
    query_telemetry,
    search_knowledge,
    search_messages,
    search_sla,
    search_visual_evidence,
)

__all__ = [
    "get_dependency_chain",
    "search_knowledge",
    "query_telemetry",
    "search_messages",
    "search_sla",
    "get_deployments",
    "get_incident",
    "list_incidents",
    "search_visual_evidence",
    "get_visual_asset",
]

