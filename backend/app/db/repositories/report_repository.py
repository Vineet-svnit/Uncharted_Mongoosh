from datetime import datetime, timezone
from typing import Any
from app.db.mongo import get_database


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReportRepository:
    def __init__(self) -> None:
        pass

    @property
    def collection(self):
        return get_database()["investigation_reports"]

    def save_report(
        self,
        thread_id: str,
        run_id: str,
        report_data: dict[str, Any],
    ) -> dict[str, Any]:
        now = _now_iso()
        doc = {
            "thread_id": thread_id,
            "run_id": run_id,
            "created_at": now,
            **report_data,
        }
        # Update or insert
        self.collection.replace_one(
            {"thread_id": thread_id, "run_id": run_id},
            doc,
            upsert=True,
        )
        doc.pop("_id", None)
        return doc

    def get_report_by_thread(self, thread_id: str) -> dict[str, Any] | None:
        doc = self.collection.find_one({"thread_id": thread_id}, sort=[("created_at", -1)])
        if doc:
            doc.pop("_id", None)
        return doc

    def delete_thread_reports(self, thread_id: str) -> int:
        res = self.collection.delete_many({"thread_id": thread_id})
        return res.deleted_count

