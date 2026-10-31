"""Health Check Endpoint for AegisRCA Backend."""

from fastapi import APIRouter
from app.db.mongo import check_mongo_connection
from app.graph.builder import get_compiled_graph
from app.services.data_layer_adapter import adapter

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Verify backend health, MongoDB connectivity, and LangGraph agent initialization."""
    mongo_ok = check_mongo_connection()

    # Verify agent state graph is compiled
    try:
        graph = get_compiled_graph()
        agent_status = "initialized" if graph is not None else "error"
    except Exception:
        agent_status = "error"

    data_layer_status = "connected" if adapter.is_available() else "pending_integration"

    return {
        "status": "ok",
        "mongodb": "connected" if mongo_ok else "disconnected",
        "agent": agent_status,
        "data_layer": data_layer_status,
    }

