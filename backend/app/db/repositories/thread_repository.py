from datetime import datetime, timezone
from typing import Any
import logging
from app.db.mongo import get_database, check_mongo_connection

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ThreadRepository:
    def __init__(self) -> None:
        self._mem_store: dict[str, dict[str, Any]] = {}

    @property
    def collection(self):
        return get_database()["chat_threads"]

    def create_thread(
        self,
        thread_id: str,
        title: str = "New Investigation",
        owner_id: str = "demo-user",
    ) -> dict[str, Any]:
        now = _now_iso()
        doc = {
            "thread_id": thread_id,
            "owner_id": owner_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "last_message_at": now,
            "message_count": 0,
            "status": "active",
            "last_run_id": None,
        }
        self._mem_store[thread_id] = dict(doc)
        if check_mongo_connection():
            try:
                self.collection.insert_one(dict(doc))
            except Exception as e:
                logger.warning(f"Thread mongo insert failed: {e}")
        return doc

    def get_thread(self, thread_id: str) -> dict[str, Any] | None:
        if check_mongo_connection():
            try:
                doc = self.collection.find_one({"thread_id": thread_id})
                if doc:
                    doc.pop("_id", None)
                    return doc
            except Exception as e:
                logger.warning(f"Thread mongo find failed: {e}")
        return self._mem_store.get(thread_id)

    def list_threads(self, limit: int = 50) -> list[dict[str, Any]]:
        if check_mongo_connection():
            try:
                cursor = self.collection.find().sort("updated_at", -1).limit(limit)
                results = []
                for doc in cursor:
                    doc.pop("_id", None)
                    results.append(doc)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"Thread mongo list failed: {e}")
        sorted_mem = sorted(
            self._mem_store.values(),
            key=lambda x: x.get("updated_at", ""),
            reverse=True,
        )
        return sorted_mem[:limit]

    def update_thread_activity(
        self,
        thread_id: str,
        last_run_id: str | None = None,
        increment_messages: int = 0,
        new_title: str | None = None,
    ) -> None:
        now = _now_iso()
        if thread_id in self._mem_store:
            t = self._mem_store[thread_id]
            t["updated_at"] = now
            t["last_message_at"] = now
            if last_run_id:
                t["last_run_id"] = last_run_id
            if new_title:
                t["title"] = new_title
            if increment_messages > 0:
                t["message_count"] = t.get("message_count", 0) + increment_messages

        if check_mongo_connection():
            try:
                update_fields: dict[str, Any] = {
                    "updated_at": now,
                    "last_message_at": now,
                }
                if last_run_id:
                    update_fields["last_run_id"] = last_run_id
                if new_title:
                    update_fields["title"] = new_title

                update_op: dict[str, Any] = {"$set": update_fields}
                if increment_messages > 0:
                    update_op["$inc"] = {"message_count": increment_messages}

                self.collection.update_one({"thread_id": thread_id}, update_op)
            except Exception as e:
                logger.warning(f"Thread mongo update failed: {e}")

    def delete_thread(self, thread_id: str) -> bool:
        existed = thread_id in self._mem_store
        self._mem_store.pop(thread_id, None)
        if check_mongo_connection():
            try:
                res = self.collection.delete_one({"thread_id": thread_id})
                return res.deleted_count > 0 or existed
            except Exception as e:
                logger.warning(f"Thread mongo delete failed: {e}")
        return existed
