"""Unit tests for AegisRCA tools."""

import json
from app.tools.retrieval_tools import (
    ALL_INVESTIGATION_TOOLS,
    list_known_incidents,
    get_incident_details,
    trace_service_dependencies,
    find_recent_deployments,
    search_engineering_knowledge,
    query_service_telemetry,
    search_incident_messages,
    retrieve_customer_sla,
    search_visual_evidence,
)


def test_all_nine_tools_registered():
    """Verify that all 9 approved investigation tools are defined and registered."""
    tool_names = [t.name for t in ALL_INVESTIGATION_TOOLS]
    assert len(tool_names) == 9
    assert "list_known_incidents" in tool_names
    assert "get_incident_details" in tool_names
    assert "trace_service_dependencies" in tool_names
    assert "find_recent_deployments" in tool_names
    assert "search_engineering_knowledge" in tool_names
    assert "query_service_telemetry" in tool_names
    assert "search_incident_messages" in tool_names
    assert "retrieve_customer_sla" in tool_names
    assert "search_visual_evidence" in tool_names


def test_tools_have_schemas_and_descriptions():
    """Verify each tool has clean descriptions and valid parameter schemas."""
    for tool in ALL_INVESTIGATION_TOOLS:
        assert tool.description is not None
        assert len(tool.description.strip()) > 10
        assert hasattr(tool, "args_schema") or hasattr(tool, "args")


def test_tool_empty_inputs_handled_gracefully():
    """Verify tools handle queries without crashing when data_layer is pending."""
    res = list_known_incidents.invoke({})
    parsed = json.loads(res)
    assert "status" in parsed

