"""LangGraph StateGraph Builder for AegisRCA."""

import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.db.mongo import get_mongo_client, check_mongo_connection
from app.graph.state import AgentState
from app.graph.planner import plan_investigation
from app.graph.nodes import agent_node, execute_tools
from app.graph.verifier import verify_evidence
from app.graph.report_generator import generate_report
from app.graph.routing import (
    route_after_planner,
    route_after_agent,
    route_after_verifier,
)

logger = logging.getLogger(__name__)

_cached_graph = None
_cached_checkpointer = None


def get_checkpointer():
    """Initialize MongoDBSaver if MongoDB is available, or fallback to MemorySaver."""
    global _cached_checkpointer
    if _cached_checkpointer is not None:
        return _cached_checkpointer

    if check_mongo_connection():
        try:
            client = get_mongo_client()
            _cached_checkpointer = MongoDBSaver(
                client=client,
                db_name=settings.mongodb_db_name,
                checkpoint_collection_name="langgraph_checkpoints",
                writes_collection_name="langgraph_checkpoint_writes",
            )
            logger.info("MongoDBSaver initialized successfully.")
            return _cached_checkpointer
        except Exception as e:
            logger.warning(f"Could not initialize MongoDBSaver ({e}), falling back to MemorySaver.")

    _cached_checkpointer = MemorySaver()
    return _cached_checkpointer


def build_graph(checkpointer=None):
    """Build and compile the LangGraph Orchestrator StateGraph."""
    builder = StateGraph(AgentState)

    # 1. Register Graph Nodes
    builder.add_node("planner", plan_investigation)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", execute_tools)
    builder.add_node("verifier", verify_evidence)
    builder.add_node("report_generator", generate_report)

    # 2. Add Transitions and Conditional Edges
    builder.add_edge(START, "planner")

    builder.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "agent": "agent",
            "report_generator": "report_generator",
        },
    )

    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {
            "tools": "tools",
            "verifier": "verifier",
        },
    )

    builder.add_edge("tools", "agent")

    builder.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {
            "agent": "agent",
            "report_generator": "report_generator",
        },
    )

    builder.add_edge("report_generator", END)

    # 3. Compile Graph with persistent checkpointer
    effective_checkpointer = checkpointer or get_checkpointer()
    compiled = builder.compile(checkpointer=effective_checkpointer)
    return compiled


def get_compiled_graph():
    global _cached_graph
    if _cached_graph is None:
        _cached_graph = build_graph()
    return _cached_graph

