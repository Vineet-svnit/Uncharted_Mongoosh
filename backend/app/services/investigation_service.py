"""Investigation Service for running the LangGraph Agent and SSE streaming."""

import uuid
import json
import asyncio
import logging
from typing import AsyncGenerator, Any
from langchain_core.messages import HumanMessage

from app.graph.builder import get_compiled_graph
from app.db.repositories.run_repository import RunRepository
from app.db.repositories.report_repository import ReportRepository
from app.services.chat_service import chat_service
from app.services.thread_service import thread_service

logger = logging.getLogger(__name__)

# Concurrency lock per thread
_thread_locks: dict[str, asyncio.Lock] = {}
_locks_guard = asyncio.Lock()


async def _get_thread_lock(thread_id: str) -> asyncio.Lock:
    async with _locks_guard:
        if thread_id not in _thread_locks:
            _thread_locks[thread_id] = asyncio.Lock()
        return _thread_locks[thread_id]


class InvestigationService:
    def __init__(self) -> None:
        self.run_repo = RunRepository()
        self.report_repo = ReportRepository()

    def _sse_pack(self, event: str, data: dict[str, Any]) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"

    async def stream_investigation(
        self, thread_id: str, message_text: str
    ) -> AsyncGenerator[str, None]:
        """Stream real-time investigation progress and results via Server-Sent Events (SSE)."""
        lock = await _get_thread_lock(thread_id)

        async with lock:
            run_id = str(uuid.uuid4())

            # 1. Start event
            yield self._sse_pack("run_started", {"run_id": run_id, "thread_id": thread_id})

            try:
                # 2. Persist user message
                chat_service.record_user_message(
                    thread_id=thread_id,
                    content=message_text,
                    run_id=run_id,
                )

                # 3. Create run record
                try:
                    self.run_repo.create_run(
                        run_id=run_id, thread_id=thread_id, query=message_text
                    )
                except Exception as e:
                    logger.warning(f"Could not persist initial run record: {e}")

                yield self._sse_pack(
                    "status",
                    {"stage": "planning", "message": "Understanding the incident query"},
                )

                # 4. Invoke LangGraph with thread_id for checkpoint recovery
                graph = get_compiled_graph()
                config = {"configurable": {"thread_id": thread_id}}

                inputs = {
                    "messages": [HumanMessage(content=message_text)],
                    "run_id": run_id,
                    "thread_id": thread_id,
                    "investigation_plan": {},
                    "evidence_items": [],
                    "verification_feedback": None,
                    "verification_attempts": 0,
                    "tool_iterations": 0,
                    "investigation_result": None,
                    "investigation_status": "in_progress",
                }

                # Stream node transitions
                final_state = None
                async for event in graph.astream(inputs, config=config, stream_mode="updates"):
                    for node_name, node_output in event.items():
                        if node_name == "planner":
                            plan = node_output.get("investigation_plan", {})
                            if plan.get("needs_clarification"):
                                yield self._sse_pack(
                                    "status",
                                    {
                                        "stage": "clarification",
                                        "message": plan.get("clarification_question", "Clarification needed"),
                                    },
                                )
                            else:
                                sources = plan.get("required_sources", [])
                                yield self._sse_pack(
                                    "status",
                                    {
                                        "stage": "planning_complete",
                                        "message": f"Identified scope. Required investigation sources: {', '.join(sources)}",
                                    },
                                )

                        elif node_name == "agent":
                            messages = node_output.get("messages", [])
                            last_msg = messages[-1] if messages else None
                            if last_msg and getattr(last_msg, "tool_calls", None):
                                for tc in last_msg.tool_calls:
                                    t_name = tc.get("name")
                                    yield self._sse_pack(
                                        "tool_started",
                                        {
                                            "tool": t_name,
                                            "message": f"Running investigation tool: {t_name}",
                                        },
                                    )

                        elif node_name == "tools":
                            tool_msgs = node_output.get("messages", [])
                            ev_items = node_output.get("evidence_items", [])
                            if tool_msgs:
                                # Distribute evidence items evenly across the tools that ran this batch
                                batch_ev_count = len(ev_items)
                                per_tool_count = max(1, batch_ev_count // len(tool_msgs)) if batch_ev_count > 0 else 0
                                for idx, tm in enumerate(tool_msgs):
                                    t_name = getattr(tm, "name", None) or "investigation_tool"
                                    # Last tool in batch gets any remainder
                                    ev_for_this = (
                                        batch_ev_count - per_tool_count * (len(tool_msgs) - 1)
                                        if idx == len(tool_msgs) - 1
                                        else per_tool_count
                                    ) if batch_ev_count > 0 else 0
                                    yield self._sse_pack(
                                        "tool_completed",
                                        {
                                            "tool": t_name,
                                            "evidence_count": ev_for_this,
                                        },
                                    )
                            else:
                                yield self._sse_pack(
                                    "tool_completed",
                                    {
                                        "tool": "investigation_tools",
                                        "evidence_count": len(ev_items),
                                    },
                                )

                        elif node_name == "verifier":
                            yield self._sse_pack(
                                "status",
                                {
                                    "stage": "verification",
                                    "message": "Cross-checking supporting and contradictory evidence",
                                },
                            )

                        elif node_name == "report_generator":
                            final_state = node_output

                # Fetch full state if not captured in update
                if not final_state:
                    state_snapshot = graph.get_state(config)
                    final_state = state_snapshot.values if state_snapshot else {}

                inv_result = final_state.get("investigation_result") or {}
                summary = inv_result.get("summary") or "Investigation completed."
                citations = inv_result.get("citations", [])

                # 5. Persist assistant message
                assistant_msg = chat_service.record_assistant_message(
                    thread_id=thread_id,
                    content=summary,
                    run_id=run_id,
                    investigation_result=inv_result,
                    citations=citations,
                )

                # 6. Persist final report
                if inv_result:
                    try:
                        self.report_repo.save_report(
                            thread_id=thread_id,
                            run_id=run_id,
                            report_data=inv_result,
                        )
                    except Exception as err:
                        logger.warning(f"Could not persist report to MongoDB: {err}")

                # 7. Update run record
                try:
                    self.run_repo.update_run_status(
                        run_id=run_id,
                        status=final_state.get("investigation_status", "completed"),
                        evidence_count=len(final_state.get("evidence_items", [])),
                    )
                except Exception as err:
                    logger.warning(f"Could not finalize run record: {err}")

                # 8. Emit assistant_result event
                yield self._sse_pack(
                    "assistant_result",
                    {
                        "message_id": assistant_msg.get("message_id", str(uuid.uuid4())),
                        "content": summary,
                        "investigation_result": inv_result,
                    },
                )

                # 9. Emit done event
                yield self._sse_pack("done", {"run_id": run_id, "thread_id": thread_id})

            except Exception as e:
                logger.error(f"Error during investigation execution: {e}", exc_info=True)
                try:
                    self.run_repo.update_run_status(
                        run_id=run_id,
                        status="failed",
                        error=str(e),
                    )
                except Exception:
                    pass

                yield self._sse_pack(
                    "error",
                    {
                        "code": "INVESTIGATION_FAILED",
                        "message": f"Unable to complete the investigation: {str(e)}",
                    },
                )


investigation_service = InvestigationService()
