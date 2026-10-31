import logging
import time
from pymongo import MongoClient
from pymongo.database import Database
from app.config import settings

logger = logging.getLogger(__name__)

_mongo_client: MongoClient | None = None
_last_ping_time = 0.0
_is_connected = False


def get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(
            settings.mongodb_uri,
            serverSelectionTimeoutMS=1000,
            connectTimeoutMS=1000,
        )
    return _mongo_client


def get_database() -> Database:
    client = get_mongo_client()
    return client[settings.mongodb_db_name]


def check_mongo_connection() -> bool:
    """Cached connectivity check to avoid repeated timeout delays when MongoDB is offline."""
    global _last_ping_time, _is_connected
    now = time.time()
    # Cache status for 5 seconds
    if now - _last_ping_time < 5.0:
        return _is_connected

    _last_ping_time = now
    try:
        client = get_mongo_client()
        client.admin.command("ping")
        _is_connected = True
        return True
    except Exception as e:
        _is_connected = False
        logger.debug(f"MongoDB ping check failed: {e}")
        return False


def close_mongo_client() -> None:
    global _mongo_client
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
