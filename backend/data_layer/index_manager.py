"""
backend/data_layer/index_manager.py
-------------------------------------
Creates and verifies all MongoDB indexes:
  • Ordinary B-tree indexes
  • MongoDB Atlas Search (BM25) indexes
  • MongoDB Atlas Vector Search indexes

The function `ensure_all_indexes()` is idempotent: safe to call every
startup.  The function `wait_for_search_indexes()` blocks until Atlas
Search / Vector Search indexes report READY status.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database
from pymongo.errors import OperationFailure

from .config import cfg
from .mongo import get_db

logger = logging.getLogger(__name__)

# ── Timeout for index readiness polling ───────────────────────────────────────
INDEX_READY_TIMEOUT_S = 300  # 5 minutes
INDEX_POLL_INTERVAL_S = 5


# ── Ordinary indexes ──────────────────────────────────────────────────────────

def _ensure_regular_indexes(db: Database) -> None:
    """Create all ordinary B-tree indexes."""

    # services
    svc = db[cfg.col_services]
    svc.create_index([("service_id", ASCENDING)], unique=True, name="svc_id_uniq")
    svc.create_index([("environment", ASCENDING), ("topology_version", ASCENDING)],
                     name="svc_env_topo")

    # deployments
    dep = db[cfg.col_deployments]
    dep.create_index([("deployment_id", ASCENDING)], unique=True, name="dep_id_uniq")
    dep.create_index([("service_id", ASCENDING), ("deployed_at", ASCENDING)],
                     name="dep_svc_time")
    dep.create_index([("pr_number", ASCENDING), ("commit_hash", ASCENDING)],
                     name="dep_pr_commit")

    # telemetry_events
    tel = db[cfg.col_telemetry]
    tel.create_index(
        [("service_id", ASCENDING), ("environment", ASCENDING), ("timestamp", ASCENDING)],
        name="tel_svc_env_ts"
    )
    tel.create_index([("incident_id", ASCENDING), ("timestamp", ASCENDING)],
                     name="tel_inc_ts")
    tel.create_index([("metric_name", ASCENDING)], name="tel_metric")

    # incident_messages
    msg = db[cfg.col_messages]
    msg.create_index([("message_id", ASCENDING)], unique=True, name="msg_id_uniq")
    msg.create_index([("incident_id", ASCENDING), ("timestamp", ASCENDING)],
                     name="msg_inc_ts")
    msg.create_index([("channel", ASCENDING)], name="msg_channel")

    # sla_clauses
    sla = db[cfg.col_sla]
    sla.create_index([("customer_id", ASCENDING), ("contract_version", ASCENDING)],
                     name="sla_cust_ver")

    # incidents
    inc = db[cfg.col_incidents]
    inc.create_index([("incident_id", ASCENDING)], unique=True, name="inc_id_uniq")
    inc.create_index([("status", ASCENDING), ("start_time", ASCENDING)],
                     name="inc_status_ts")

    # knowledge_chunks
    kc = db[cfg.col_knowledge]
    kc.create_index([("document_id", ASCENDING)], unique=True, name="doc_id_uniq")
    kc.create_index([("source_type", ASCENDING)], name="kc_source_type")

    # visual_evidence
    ve = db[cfg.col_visual]
    ve.create_index([("evidence_id", ASCENDING)], unique=True, name="ev_id_uniq")

    # investigation_reports — index for future use
    rep = db[cfg.col_reports]
    rep.create_index([("incident_id", ASCENDING)], name="rep_inc_id")

    logger.info("Regular indexes created / verified.")


# ── Atlas Search (BM25) index definitions ─────────────────────────────────────
# NOTE: MongoDB Atlas Free Tier (M0) allows a maximum of 3 search indexes across
# the entire cluster. To strictly obey this limit, we keep only the 3 Vector Search
# indexes defined in _VECTOR_INDEXES below and omit BM25 text search indexes.
_SEARCH_INDEXES: list[dict[str, Any]] = []

# ── Atlas Vector Search index definitions (Exactly 3 indexes for Atlas Free Tier) ─
_VECTOR_INDEXES: list[dict[str, Any]] = [
    {
        "collection": cfg.col_knowledge,
        "name": cfg.vector_idx_knowledge,
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": cfg.embedding_dimensions,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "source_type"},
                {"type": "filter", "path": "service_id"},
                {"type": "filter", "path": "incident_id"},
                {"type": "filter", "path": "customer_id"},
                {"type": "filter", "path": "environment"},
            ]
        },
    },
    {
        "collection": cfg.col_messages,
        "name": cfg.vector_idx_messages,
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": cfg.embedding_dimensions,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "incident_id"},
                {"type": "filter", "path": "channel"},
            ]
        },
    },
    {
        "collection": cfg.col_visual,
        "name": cfg.vector_idx_visual,
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": cfg.embedding_dimensions,
                    "similarity": "cosine",
                },
                {"type": "filter", "path": "incident_id"},
            ]
        },
    },
]


def _clean_non_vector_search_indexes(db: Database) -> None:
    """
    Ensure no legacy BM25 / text search indexes occupy slots on MongoDB Atlas Free Tier (max 3).
    Drops any search index on collections that is not one of our 3 designated vector indexes.
    """
    valid_vector_names = {idx["name"] for idx in _VECTOR_INDEXES}
    cols_to_check = set(db.list_collection_names()) | {cfg.col_knowledge, cfg.col_messages, cfg.col_visual}
    dropped_any = False

    for col_name in cols_to_check:
        if col_name.startswith("system.") or col_name.startswith("fs."):
            continue
        try:
            col = db[col_name]
            for info in list(col.list_search_indexes()):
                name = info.get("name")
                # If this search index is not one of our 3 valid vector indexes, drop it to free quota
                if name and name not in valid_vector_names:
                    logger.info("Dropping legacy search index '%s' on '%s' (Atlas free tier allows max 3).", name, col_name)
                    try:
                        col.drop_search_index(name)
                        dropped_any = True
                    except Exception as drop_exc:
                        logger.warning("Could not drop search index '%s': %s", name, drop_exc)
        except Exception:
            pass

    if dropped_any:
        logger.info("Waiting 6 seconds for Atlas Search nodes to release dropped index quota …")
        time.sleep(6)


def _create_search_index(db: Database, collection: str, name: str, definition: dict) -> None:
    """Create a single Atlas Search index, ignoring 'already exists' errors."""
    if collection not in db.list_collection_names():
        db.create_collection(collection)
    col = db[collection]
    try:
        col.create_search_index({"name": name, "definition": definition})
        logger.info("Created search index '%s' on '%s'.", name, collection)
    except OperationFailure as exc:
        msg = str(exc).lower()
        if "already exists" in msg or "duplicate" in msg or exc.code in (68, 85):
            logger.debug("Search index '%s' on '%s' already exists, skipping.", name, collection)
        else:
            raise


def _create_vector_index(db: Database, collection: str, name: str, definition: dict) -> None:
    """Create a single Atlas Vector Search index, skipping if it already exists."""
    if collection not in db.list_collection_names():
        db.create_collection(collection)
    col = db[collection]

    # Pre-check: If index already exists on this collection, skip creation
    # to avoid Atlas cluster-level quota rejection
    try:
        existing = list(col.list_search_indexes())
        for idx_info in existing:
            if idx_info.get("name") == name:
                logger.info(
                    "Vector index '%s' on '%s' already exists (status: %s), skipping creation.",
                    name,
                    collection,
                    idx_info.get("status", "ACTIVE"),
                )
                return
    except Exception as check_exc:
        logger.debug("Could not check existing search indexes on '%s': %s", collection, check_exc)

    try:
        col.create_search_index(
            {"name": name, "definition": definition, "type": "vectorSearch"}
        )
        logger.info("Created vector index '%s' on '%s'.", name, collection)
    except OperationFailure as exc:
        msg = str(exc).lower()
        if "already exists" in msg or "duplicate" in msg or exc.code in (68, 85):
            logger.debug("Vector index '%s' on '%s' already exists, skipping.", name, collection)
        elif "maximum number of fts indexes" in msg:
            logger.warning(
                "Atlas Free Tier quota reached while creating '%s' on '%s'. "
                "If old indexes exist on your Atlas cluster, run cleanup_atlas_indexes.py or check the Atlas UI.",
                name,
                collection,
            )
        else:
            raise


def ensure_all_indexes(db: Database | None = None) -> None:
    """Create all ordinary B-tree indexes and the 3 vector search indexes (for Atlas Free Tier)."""
    db = get_db() if db is None else db
    _ensure_regular_indexes(db)

    # Free up slots on Atlas if any non-vector search indexes exist
    _clean_non_vector_search_indexes(db)

    for idx in _SEARCH_INDEXES:
        _create_search_index(db, idx["collection"], idx["name"], idx["definition"])

    for idx in _VECTOR_INDEXES:
        _create_vector_index(db, idx["collection"], idx["name"], idx["definition"])

    logger.info("All 3 vector indexes configured for Atlas Free Tier. Run wait_for_search_indexes() to confirm readiness.")


def _list_search_index_status(db: Database) -> dict[str, dict[str, str]]:
    """
    Returns {collection: {index_name: status}} for all Atlas Search / Vector
    Search indexes we care about.
    """
    wanted: dict[str, set[str]] = {}
    for idx in _SEARCH_INDEXES + _VECTOR_INDEXES:
        wanted.setdefault(idx["collection"], set()).add(idx["name"])

    status: dict[str, dict[str, str]] = {}
    for collection, names in wanted.items():
        col = db[collection]
        try:
            for info in col.list_search_indexes():
                if info["name"] in names:
                    status.setdefault(collection, {})[info["name"]] = info.get(
                        "status", "UNKNOWN"
                    )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not list indexes for '%s': %s", collection, exc)
    return status


def wait_for_search_indexes(
    db: Database | None = None,
    timeout: int = INDEX_READY_TIMEOUT_S,
) -> bool:
    """
    Poll until all Atlas Search and Vector Search indexes are READY.
    Returns True if all are ready, False on timeout.
    """
    db = get_db() if db is None else db
    deadline = time.time() + timeout

    all_wanted: set[tuple[str, str]] = set()
    for idx in _SEARCH_INDEXES + _VECTOR_INDEXES:
        all_wanted.add((idx["collection"], idx["name"]))

    while time.time() < deadline:
        status = _list_search_index_status(db)
        ready: set[tuple[str, str]] = set()
        not_ready: list[tuple[str, str, str]] = []

        for collection, names_status in status.items():
            for name, s in names_status.items():
                if s == "READY":
                    ready.add((collection, name))
                else:
                    not_ready.append((collection, name, s))

        missing = all_wanted - {(c, n) for c, n in ready} - {
            (c, n) for c, n, _ in not_ready
        }

        if not not_ready and not missing:
            logger.info("All search indexes are READY.")
            return True

        for col, name, s in not_ready:
            logger.info("  Waiting for index '%s' on '%s' … status=%s", name, col, s)
        for col, name in missing:
            logger.info("  Index '%s' on '%s' not yet visible.", name, col)

        time.sleep(INDEX_POLL_INTERVAL_S)

    logger.error(
        "Timeout waiting for search indexes to become READY after %ds.", timeout
    )
    return False


def check_mongodb_version(db: Database | None = None) -> str:
    """Return the MongoDB server version string."""
    db = get_db() if db is None else db
    info = db.client.server_info()
    version = info.get("version", "unknown")
    major = int(version.split(".")[0]) if version != "unknown" else 0
    if major < 8:
        logger.warning(
            "MongoDB %s detected. $rankFusion requires MongoDB 8.0+. "
            "Hybrid search will fall back to vector-only.",
            version,
        )
    else:
        logger.info("MongoDB %s detected. $rankFusion supported.", version)
    return version

