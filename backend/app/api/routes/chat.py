"""Chat and Investigation API Routes."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas.chat import (
    ThreadCreateRequest,
    ThreadResponse,
    ThreadListResponse,
    ThreadMessagesResponse,
    ChatMessageResponse,
    SendMessageRequest,
)
from app.services.thread_service import thread_service
from app.services.chat_service import chat_service
from app.services.investigation_service import investigation_service

router = APIRouter(prefix="/api/chat", tags=["Chat & Investigations"])


@router.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(req: ThreadCreateRequest | None = None):
    """Create a new conversational investigation thread."""
    title = req.title if req else None
    created = thread_service.create_thread(title=title)
    return ThreadResponse(**created)


@router.get("/threads", response_model=ThreadListResponse)
def list_conversations(limit: int = 50):
    """List all investigation threads ordered by most recent activity."""
    threads = thread_service.list_threads(limit=limit)
    return ThreadListResponse(threads=[ThreadResponse(**t) for t in threads])


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
def get_conversation(thread_id: str):
    """Retrieve metadata for a specific conversation thread."""
    t = thread_service.get_thread(thread_id=thread_id)
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread '{thread_id}' not found.",
        )
    return ThreadResponse(**t)


@router.get("/threads/{thread_id}/messages", response_model=ThreadMessagesResponse)
def get_conversation_messages(thread_id: str, limit: int = 100):
    """Retrieve full chronological conversation history for a thread."""
    t = thread_service.get_thread(thread_id=thread_id)
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread '{thread_id}' not found.",
        )
    msgs = chat_service.get_messages(thread_id=thread_id, limit=limit)
    return ThreadMessagesResponse(
        thread_id=thread_id,
        messages=[ChatMessageResponse(**m) for m in msgs],
    )


@router.post("/threads/{thread_id}/messages/stream")
async def send_message_and_stream(thread_id: str, req: SendMessageRequest):
    """Send an inquiry to the agent and stream investigation planning, tools, and report via SSE."""
    # Ensure thread exists or initialize automatically
    t = thread_service.get_thread(thread_id=thread_id)
    if not t:
        # Create thread if not present to ensure seamless experience
        t = thread_service.create_thread(title=req.message[:40])
        thread_id = t["thread_id"]

    generator = investigation_service.stream_investigation(
        thread_id=thread_id,
        message_text=req.message,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.delete("/threads/{thread_id}")
def delete_conversation(thread_id: str):
    """Delete conversation thread and cascade-delete its messages, runs, reports, and checkpoints."""
    t = thread_service.get_thread(thread_id=thread_id)
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thread '{thread_id}' not found.",
        )
    thread_service.delete_thread(thread_id=thread_id)
    return {"status": "success", "message": f"Thread '{thread_id}' and all associated records deleted."}

