"""Thread Service for AegisRCA Conversation Management."""

import uuid
import logging
from typing import Any
from app.db.repositories.thread_repository import ThreadRepository
from app.db.repositories.message_repository import MessageRepository
from app.db.repositories.run_repository import RunRepository
from app.db.repositories.report_repository import ReportRepository
from app.graph.builder import get_checkpointer

logger = logging.getLogger(__name__)


class ThreadService:
    def __init__(self) -> None:
        self.thread_repo = ThreadRepository()
        self.msg_repo = MessageRepository()
        self.run_repo = RunRepository()
        self.report_repo = ReportRepository()

    def create_thread(self, title: str | None = None) -> dict[str, Any]:
        thread_id = str(uuid.uuid4())
        thread_title = title.strip() if title and title.strip() else "New Investigation"
        return self.thread_repo.create_thread(thread_id=thread_id, title=thread_title)

    def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        return self.thread_repo.get_thread(thread_id=thread_id)

    def list_threads(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.thread_repo.list_threads(limit=limit)

    def delete_thread(self, thread_id: str) -> bool:
        """Cascade deletes thread, chat messages, investigation runs, reports, and checkpointer state."""
        try:
            # 1. Delete messages
            self.msg_repo.delete_thread_messages(thread_id=thread_id)
            # 2. Delete runs
            self.run_repo.delete_thread_runs(thread_id=thread_id)
            # 3. Delete reports
            self.report_repo.delete_thread_reports(thread_id=thread_id)
            # 4. Delete thread document
            deleted = self.thread_repo.delete_thread(thread_id=thread_id)
            # 5. Delete LangGraph checkpoints
            try:
                cp = get_checkpointer()
                if hasattr(cp, "delete_thread"):
                    cp.delete_thread(thread_id=thread_id)
            except Exception as cp_err:
                logger.warning(f"Checkpointer thread state cleanup note: {cp_err}")

            return deleted
        except Exception as e:
            logger.error(f"Error deleting thread {thread_id}: {e}")
            return False


thread_service = ThreadService()
