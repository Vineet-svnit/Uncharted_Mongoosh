from datetime import datetime, timezone
from typing import Any
import logging
from app.db.mongo import get_database, check_mongo_connection

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MessageRepository:
    def __init__(self) -> None:
        self._mem_store: dict[str, list[dict[str, Any]]] = {}

    @property
    def collection(self):
        return get_database()["chat_messages"]

    def save_message(
        self,
        message_id: str,
        thread_id: str,
        role: str,
        content: str,
        run_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = _now_iso()
        doc = {
            "message_id": message_id,
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "created_at": now,
            "run_id": run_id,
            "metadata": metadata or {},
        }
        if thread_id not in self._mem_store:
            self._mem_store[thread_id] = []
        self._mem_store[thread_id].append(dict(doc))

        if check_mongo_connection():
            try:
                self.collection.insert_one(dict(doc))
            except Exception as e:
                logger.warning(f"Message mongo insert failed: {e}")
        return doc

    def get_thread_messages(self, thread_id: str, limit: int = 100) -> list[dict[str, Any]]:
        if check_mongo_connection():
            try:
                cursor = self.collection.find({"thread_id": thread_id}).sort("created_at", 1).limit(limit)
                results = []
                for doc in cursor:
                    doc.pop("_id", None)
                    results.append(doc)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"Message mongo list failed: {e}")
        return self._mem_store.get(thread_id, [])[:limit]

    def delete_thread_messages(self, thread_id: str) -> int:
        mem_count = len(self._mem_store.pop(thread_id, []))
        if check_mongo_connection():
            try:
                res = self.collection.delete_many({"thread_id": thread_id})
                return res.deleted_count
            except Exception as e:
                logger.warning(f"Message mongo delete failed: {e}")
        return mem_count
