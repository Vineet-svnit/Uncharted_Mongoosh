from datetime import datetime, timezone
from typing import Any
from app.db.mongo import get_database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRepository:
    def __init__(self) -> None:
        pass

    @property
    def collection(self):
        return get_database()["investigation_runs"]

    def create_run(self, run_id: str, thread_id: str, query: str) -> dict[str, Any]:
        now = _now_iso()
        doc = {
            "run_id": run_id,
            "thread_id": thread_id,
            "status": "in_progress",
            "query": query,
            "started_at": now,
            "completed_at": None,
            "tool_events": [],
            "evidence_count": 0,
            "error": None,
        }
        self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc

    def add_tool_event(
        self,
        run_id: str,
        tool_name: str,
        started_at: str,
        completed_at: str | None = None,
        result_count: int = 0,
        status: str = "completed",
        error: str | None = None,
    ) -> None:
        event = {
            "tool_name": tool_name,
            "status": status,
            "started_at": started_at,
            "completed_at": completed_at or _now_iso(),
            "result_count": result_count,
            "error": error,
        }
        self.collection.update_one(
            {"run_id": run_id},
            {
                "$push": {"tool_events": event},
                "$inc": {"evidence_count": result_count},
            },
        )

    def update_run_status(
        self,
        run_id: str,
        status: str,
        evidence_count: int | None = None,
        error: str | None = None,
    ) -> None:
        now = _now_iso()
        update_fields: dict[str, Any] = {
            "status": status,
            "completed_at": now,
        }
        if evidence_count is not None:
            update_fields["evidence_count"] = evidence_count
        if error:
            update_fields["error"] = error

        self.collection.update_one({"run_id": run_id}, {"$set": update_fields})

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        doc = self.collection.find_one({"run_id": run_id})
        if doc:
            doc.pop("_id", None)
        return doc

    def delete_thread_runs(self, thread_id: str) -> int:
        res = self.collection.delete_many({"thread_id": thread_id})
        return res.deleted_count

