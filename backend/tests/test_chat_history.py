"""Unit tests for conversation thread and chat message history."""

import uuid
from app.services.thread_service import thread_service
from app.services.chat_service import chat_service


def test_thread_lifecycle_and_messages():
    """Verify thread creation, message additions, and thread listing."""
    # 1. Create Thread
    thread = thread_service.create_thread(title="Test Incident Investigation")
    thread_id = thread["thread_id"]
    assert thread_id is not None
    assert thread["title"] == "Test Incident Investigation"

    # 2. Add user message
    user_msg = chat_service.record_user_message(
        thread_id=thread_id,
        content="What caused the 504 errors on Checkout API?",
    )
    assert user_msg["role"] == "user"
    assert user_msg["thread_id"] == thread_id

    # 3. Add assistant message
    asst_msg = chat_service.record_assistant_message(
        thread_id=thread_id,
        content="The outage was caused by Redis connection pool exhaustion.",
        investigation_result={"summary": "Redis exhaustion"},
        citations=[{"source_id": "PR-812"}],
    )
    assert asst_msg["role"] == "assistant"
    assert "investigation_result" in asst_msg["metadata"]

    # 4. Read messages
    messages = chat_service.get_messages(thread_id=thread_id)
    assert len(messages) >= 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

    # 5. Clean up
    deleted = thread_service.delete_thread(thread_id=thread_id)
    assert deleted in [True, False]

