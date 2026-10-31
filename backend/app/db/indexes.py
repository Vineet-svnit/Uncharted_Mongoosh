import logging
from pymongo import ASCENDING, DESCENDING
from app.db.mongo import get_database

logger = logging.getLogger(__name__)


def ensure_indexes() -> None:
    """Ensure indexes on chat and investigation collections."""
    try:
        db = get_database()

        # chat_threads
        db["chat_threads"].create_index([("thread_id", ASCENDING)], unique=True)
        db["chat_threads"].create_index([("updated_at", DESCENDING)])

        # chat_messages
        db["chat_messages"].create_index([("message_id", ASCENDING)], unique=True)
        db["chat_messages"].create_index([("thread_id", ASCENDING), ("created_at", ASCENDING)])

        # investigation_runs
        db["investigation_runs"].create_index([("run_id", ASCENDING)], unique=True)
        db["investigation_runs"].create_index([("thread_id", ASCENDING)])

        # investigation_reports
        db["investigation_reports"].create_index([("thread_id", ASCENDING)])
        db["investigation_reports"].create_index([("incident_id", ASCENDING)])

        logger.info("MongoDB collections and indexes ensured successfully.")
    except Exception as e:
        logger.warning(f"Failed to ensure MongoDB indexes (database may be unreachable): {e}")

