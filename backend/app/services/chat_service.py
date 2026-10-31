"""Chat Service for managing conversation message history."""

import uuid
import logging
from typing import Any
from app.db.repositories.message_repository import MessageRepository
from app.db.repositories.thread_repository import ThreadRepository

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self) -> None:
        self.msg_repo = MessageRepository()
        self.thread_repo = ThreadRepository()

    def record_user_message(
        self, thread_id: str, content: str, run_id: str | None = None
    ) -> dict[str, Any]:
        message_id = str(uuid.uuid4())
        doc = self.msg_repo.save_message(
            message_id=message_id,
            thread_id=thread_id,
            role="user",
            content=content,
            run_id=run_id,
            metadata={},
        )
        thread = self.thread_repo.get_thread(thread_id)
        new_title = None
        if thread and thread.get("message_count", 0) == 0:
            new_title = content[:40] + ("..." if len(content) > 40 else "")

        self.thread_repo.update_thread_activity(
            thread_id=thread_id,
            last_run_id=run_id,
            increment_messages=1,
            new_title=new_title,
        )
        return doc

    def record_assistant_message(
        self,
        thread_id: str,
        content: str,
        run_id: str | None = None,
        investigation_result: dict[str, Any] | None = None,
        citations: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        message_id = str(uuid.uuid4())
        metadata: dict[str, Any] = {}
        if investigation_result:
            metadata["investigation_result"] = investigation_result
        if citations:
            metadata["citations"] = citations

        doc = self.msg_repo.save_message(
            message_id=message_id,
            thread_id=thread_id,
            role="assistant",
            content=content,
            run_id=run_id,
            metadata=metadata,
        )
        self.thread_repo.update_thread_activity(
            thread_id=thread_id,
            last_run_id=run_id,
            increment_messages=1,
        )
        return doc

    def get_messages(self, thread_id: str, limit: int = 100) -> list[dict[str, Any]]:
        return self.msg_repo.get_thread_messages(thread_id=thread_id, limit=limit)


chat_service = ChatService()
