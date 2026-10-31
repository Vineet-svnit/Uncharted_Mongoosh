"""
backend/data_layer/mongo.py
---------------------------
Singleton PyMongo client and convenience database/collection accessors.
Keeps all connection logic in one place.
"""

from __future__ import annotations

import gridfs
from pymongo import MongoClient
from pymongo.database import Database

from .config import cfg

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return the singleton PyMongo client, creating it if necessary."""
    global _client
    if _client is None:
        _client = MongoClient(cfg.mongodb_uri, serverSelectionTimeoutMS=10_000)
        # Trigger a quick connectivity check
        _client.admin.command("ping")
    return _client


def get_db() -> Database:
    """Return the AegisRCA database handle."""
    return get_client()[cfg.mongodb_db_name]


def get_gridfs() -> gridfs.GridFS:
    """Return a GridFS handle on the AegisRCA database."""
    return gridfs.GridFS(get_db())


def close() -> None:
    """Close the MongoDB connection (useful in tests / scripts)."""
    global _client
    if _client is not None:
        _client.close()
        _client = None

