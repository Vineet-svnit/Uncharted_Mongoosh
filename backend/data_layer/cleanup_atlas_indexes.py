"""
backend/data_layer/cleanup_atlas_indexes.py
-------------------------------------------
Utility to inspect and clean up search indexes on MongoDB Atlas Free Tier (M0).
Atlas Free Tier permits at most 3 Search / Vector Search indexes across the cluster.

Usage:
    python -m data_layer.cleanup_atlas_indexes
"""

from __future__ import annotations

import logging
import sys
import time

from data_layer.config import cfg
from data_layer.index_manager import _VECTOR_INDEXES
from data_layer.mongo import get_client, get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")
log = logging.getLogger("atlas_cleanup")


def inspect_and_clean_cluster():
    client = get_client()
    log.info("Connecting to Atlas cluster at %s ...", cfg.mongodb_uri.split("@")[-1])

    valid_vector_names = {idx["name"] for idx in _VECTOR_INDEXES}
    all_found_indexes: list[dict] = []

    try:
        db_names = client.list_database_names()
    except Exception as e:
        log.error("Could not list databases: %s", e)
        db_names = [cfg.mongodb_db_name]

    log.info("Databases on cluster: %s", db_names)

    # 1. Scan all databases and collections for search indexes
    for db_name in db_names:
        if db_name in ("admin", "local", "config"):
            continue
        db = client[db_name]
        try:
            col_names = db.list_collection_names()
        except Exception:
            continue

        for col_name in col_names:
            if col_name.startswith("system."):
                continue
            col = db[col_name]
            try:
                for idx in col.list_search_indexes():
                    all_found_indexes.append({
                        "database": db_name,
                        "collection": col_name,
                        "name": idx.get("name"),
                        "status": idx.get("status"),
                        "type": idx.get("type", "search"),
                    })
            except Exception:
                pass

    log.info("=" * 65)
    log.info("Current Atlas Search / Vector Indexes on Cluster (%d total):", len(all_found_indexes))
    log.info("=" * 65)

    if not all_found_indexes:
        log.info("  No search indexes currently found on the cluster.")
    else:
        for idx in all_found_indexes:
            is_valid = idx["name"] in valid_vector_names and idx["database"] == cfg.mongodb_db_name
            tag = "[KEEP - VECTOR]" if is_valid else "[DELETE - NON-VECTOR / UNWANTED]"
            log.info("  %s %s.%s -> '%s' (type: %s, status: %s)",
                     tag, idx["database"], idx["collection"], idx["name"], idx["type"], idx["status"])

    log.info("-" * 65)

    # 2. Drop any index that is NOT one of our 3 desired vector indexes
    to_drop = [
        idx for idx in all_found_indexes
        if not (idx["name"] in valid_vector_names and idx["database"] == cfg.mongodb_db_name)
    ]

    if not to_drop:
        log.info("No unwanted search indexes found. All existing indexes match the 3 designated vector indexes.")
    else:
        log.info("Found %d non-vector or unwanted search indexes to drop...", len(to_drop))
        for idx in to_drop:
            col = client[idx["database"]][idx["collection"]]
            log.info("Dropping index '%s' on %s.%s ...", idx["name"], idx["database"], idx["collection"])
            try:
                col.drop_search_index(idx["name"])
            except Exception as exc:
                log.warning("Could not drop index '%s': %s", idx["name"], exc)

        log.info("Waiting for Atlas to finish releasing deleted index slots (polling up to 60s) ...")
        for _ in range(12):
            time.sleep(5)
            # Recheck
            remaining = 0
            for idx in to_drop:
                try:
                    col = client[idx["database"]][idx["collection"]]
                    names = {i.get("name") for i in col.list_search_indexes()}
                    if idx["name"] in names:
                        remaining += 1
                except Exception:
                    pass
            if remaining == 0:
                log.info("All dropped indexes have been successfully cleared by Atlas Search!")
                break
            log.info("  Still waiting on %d indexes to finish deleting...", remaining)

    log.info("=" * 65)
    log.info("Atlas search index cleanup complete.")
    log.info("You can now safely run: python -m data_layer.seed.seed_database")
    log.info("=" * 65)


if __name__ == "__main__":
    inspect_and_clean_cluster()

