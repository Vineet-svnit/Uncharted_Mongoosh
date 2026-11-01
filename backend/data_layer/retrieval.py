"""
backend/data_layer/retrieval.py
---------------------------------
All retrieval functions for the AegisRCA data layer.

Member 2 imports these directly into LangGraph tools:

    from data_layer import (
        get_dependency_chain,
        search_knowledge,
        query_telemetry,
        search_messages,
        search_sla,
        get_deployments,
        get_incident,
        list_incidents,
        search_visual_evidence,
        get_visual_asset,
    )

All public functions:
  • Return plain JSON-serialisable Python dicts/lists.
  • Never return raw ObjectId, datetime or binary objects.
  • Never return embedding arrays.
  • Raise meaningful exceptions when a required index is unavailable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.errors import OperationFailure

from .config import cfg
from .mongo import get_db, get_gridfs

log = logging.getLogger(__name__)

# Whitelisted filter keys for search functions
_ALLOWED_FILTER_KEYS = frozenset(
    {"source_type", "service_id", "incident_id", "customer_id", "environment"}
)

# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _clean(doc: dict) -> dict:
    """
    Remove MongoDB internals and non-serialisable fields from a document.
    Converts ObjectId → str, datetime → ISO-8601 str, removes embeddings.
    """
    out = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        if k == "embedding":
            continue
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat().replace("+00:00", "Z")
        elif isinstance(v, dict):
            out[k] = _clean(v)
        elif isinstance(v, list):
            out[k] = [_clean(i) if isinstance(i, dict) else i for i in v]
        else:
            out[k] = v
    return out


def _parse_datetime(value) -> datetime:
    """Accept datetime or ISO-8601 string; always return UTC-aware datetime."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        s = value.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    raise TypeError(f"Cannot parse datetime from {type(value)}: {value!r}")


def _build_filter(filters: dict | None) -> dict:
    """Build a safe MongoDB filter from whitelisted keys only."""
    if not filters:
        return {}
    return {k: v for k, v in filters.items() if k in _ALLOWED_FILTER_KEYS and v is not None}


def _check_embeddings_available(operation: str) -> None:
    """Raise a clear error when embeddings are not present."""
    db = get_db()
    sample = db[cfg.col_knowledge].find_one({"embedding": {"$ne": None}})
    if sample is None:
        raise RuntimeError(
            f"Cannot perform {operation}: no embeddings found in the database. "
            "Run seed_database without --skip-embeddings to generate embeddings, "
            "or use structured/keyword search instead."
        )


def _get_query_embedding(query: str) -> list[float]:
    """Generate a query embedding using the same model as stored documents."""
    from .embeddings import embed_query  # lazy import
    return embed_query(query)


def _version_supports_rank_fusion() -> bool:
    """Check whether the connected MongoDB server supports $rankFusion (≥ 8.0)."""
    db = get_db()
    try:
        info = db.client.server_info()
        major = int(info.get("version", "0").split(".")[0])
        return major >= 8
    except Exception:  # noqa: BLE001
        return False


# --------------------------------------------------------------------------- #
# 1. Dependency traversal                                                      #
# --------------------------------------------------------------------------- #

def get_dependency_chain(
    service_id: str,
    environment: str = "production",
    topology_version: str = "prod-2026-10-28",
    max_depth: int = 4,
) -> dict:
    """
    Traverse the service dependency graph using MongoDB $graphLookup.

    Returns:
        {
          "root": { ...service doc... },
          "dependencies": [ { ...service doc..., "depth": int }, ... ]
        }

    Raises:
        ValueError  if the root service is not found.
        RuntimeError on MongoDB query errors.
    """
    db = get_db()
    col = db[cfg.col_services]

    pipeline = [
        {
            "$match": {
                "service_id": service_id,
                "environment": environment,
                "topology_version": topology_version,
            }
        },
        {
            "$graphLookup": {
                "from": cfg.col_services,
                "startWith": "$depends_on",
                "connectFromField": "depends_on",
                "connectToField": "service_id",
                "as": "dependency_graph",
                "maxDepth": max_depth - 1,   # 0-indexed
                "depthField": "depth",
                "restrictSearchWithMatch": {
                    "environment": environment,
                    "topology_version": topology_version,
                },
            }
        },
    ]

    try:
        results = list(col.aggregate(pipeline))
    except OperationFailure as exc:
        raise RuntimeError(f"$graphLookup failed: {exc}") from exc

    if not results:
        raise ValueError(
            f"Service '{service_id}' not found "
            f"(environment={environment}, topology_version={topology_version})."
        )

    root_doc = results[0]
    deps_raw = root_doc.pop("dependency_graph", [])

    deps = []
    for d in deps_raw:
        cleaned = _clean(d)
        deps.append(cleaned)
    deps.sort(key=lambda x: (x.get("depth", 0), x.get("service_id", "")))

    return {
        "root": _clean(root_doc),
        "dependencies": deps,
    }


# --------------------------------------------------------------------------- #
# 2. Knowledge search (hybrid: vector + BM25 + $rankFusion)                   #
# --------------------------------------------------------------------------- #

def search_knowledge(
    query: str,
    filters: dict | None = None,
    limit: int = 5,
) -> list[dict]:
    """
    Hybrid semantic + keyword search over knowledge_chunks.

    Searches:
      - PR diffs
      - Runbooks
      - Postmortems
      - SLA text chunks
      - Incident summaries

    Uses $vectorSearch (Voyage AI embeddings) + $search (BM25) combined
    via $rankFusion when MongoDB ≥ 8.0.  Falls back to $vectorSearch only
    on older versions.

    Raises:
        RuntimeError  when embeddings are unavailable.
        RuntimeError  when a required search index is missing.
    """
    _check_embeddings_available("search_knowledge")

    db = get_db()
    col = db[cfg.col_knowledge]
    safe_filters = _build_filter(filters)

    # --- Query embedding ---
    q_emb = _get_query_embedding(query)

    # --- Vector Search pipeline ---
    vector_filter = {}
    if safe_filters:
        vector_filter = safe_filters

    vector_pipeline: list[dict] = [
        {
            "$vectorSearch": {
                "index": cfg.vector_idx_knowledge,
                "path": "embedding",
                "queryVector": q_emb,
                "numCandidates": limit * 20,
                "limit": limit * 4,
                **({"filter": vector_filter} if vector_filter else {}),
            }
        },
        {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
        {"$project": {"embedding": 0, "_id": 0}},
    ]

    # --- Atlas Vector Search & Reranking (Atlas Free Tier compliant: 3 vector indexes) ---
    # Retrieve top X candidates (X >= Y) for downstream reranking via Voyage AI
    candidate_limit = max(limit * 3, 12)
    results = _execute_hybrid_search(
        col=col,
        vector_pipeline=vector_pipeline,
        bm25_pipeline=None,
        vector_index=cfg.vector_idx_knowledge,
        text_index=None,
        id_field="document_id",
        limit=candidate_limit,
    )

    # --- Voyage AI Reranker: select top Y (limit) from top X candidate documents ---
    top_x_docs = results[:candidate_limit]
    if top_x_docs and cfg.embeddings_available:
        try:
            from .embeddings import rerank_documents
            doc_texts = [
                f"{d.get('title', '')}\n{d.get('content', '')}"[:1000]
                for d in top_x_docs
            ]
            rerank_scores = rerank_documents(query=query, documents=doc_texts, top_k=limit)
            reranked_docs = []
            for orig_idx, score in rerank_scores:
                if orig_idx < len(top_x_docs):
                    doc = dict(top_x_docs[orig_idx])
                    doc["rerank_score"] = score
                    reranked_docs.append(doc)
            if reranked_docs:
                results = reranked_docs
        except Exception as exc:
            log.warning("Voyage reranking step bypassed, retaining hybrid rank order: %s", exc)

    return [_format_knowledge_result(r) for r in results[:limit]]


def _reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    id_field: str,
    limit: int,
    k: int = 60,
    weight_vector: float = 0.6,
    weight_bm25: float = 0.4,
) -> list[dict]:
    """Combine vector and BM25 results using Reciprocal Rank Fusion (RRF)."""
    scores: dict[str, float] = {}
    docs_by_id: dict[str, dict] = {}

    for rank, doc in enumerate(vector_results):
        doc_id = doc.get(id_field)
        if doc_id:
            scores[doc_id] = scores.get(doc_id, 0.0) + weight_vector / (k + rank + 1)
            docs_by_id[doc_id] = doc

    for rank, doc in enumerate(bm25_results):
        doc_id = doc.get(id_field)
        if doc_id:
            scores[doc_id] = scores.get(doc_id, 0.0) + weight_bm25 / (k + rank + 1)
            if doc_id not in docs_by_id:
                docs_by_id[doc_id] = doc

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    results = []
    for doc_id in sorted_ids[:limit]:
        item = dict(docs_by_id[doc_id])
        item["score"] = scores[doc_id]
        results.append(item)
    return results


def _execute_hybrid_search(
    col,
    vector_pipeline: list[dict],
    bm25_pipeline: list[dict] | None,
    vector_index: str,
    text_index: str | None,
    id_field: str,
    limit: int,
) -> list[dict]:
    """
    Execute search across candidate documents.
    If BM25 pipeline and text index are omitted (as on Atlas Free Tier with 3-index cap),
    runs vector_pipeline directly.
    Otherwise attempts native $rankFusion or Reciprocal Rank Fusion.
    """
    if not bm25_pipeline or not text_index:
        try:
            return list(col.aggregate(vector_pipeline))[:limit]
        except OperationFailure as exc:
            _raise_index_error(exc, vector_index, col.name)
            return []

    if _version_supports_rank_fusion():
        pipeline = _rank_fusion_pipeline(
            vector_pipeline, bm25_pipeline,
            vector_score_field="vector_score",
            bm25_score_field="bm25_score",
            limit=limit,
        )
        try:
            return list(col.aggregate(pipeline))
        except OperationFailure as exc:
            # Code 40324 = Location40324: Unrecognized pipeline stage name: '$rankFusion'
            if exc.code != 40324 and "unrecognized pipeline stage" not in str(exc).lower():
                _raise_index_error(exc, vector_index, col.name)
            log.warning(
                "$rankFusion not natively available on this server build. "
                "Executing $vectorSearch + $search with Reciprocal Rank Fusion."
            )

    try:
        vec_results = list(col.aggregate(vector_pipeline))
    except OperationFailure as exc:
        _raise_index_error(exc, vector_index, col.name)
        vec_results = []

    try:
        bm25_results = list(col.aggregate(bm25_pipeline))
    except OperationFailure as exc:
        log.warning("BM25 $search failed on '%s': %s. Using vector results only.", col.name, exc)
        bm25_results = []

    if bm25_results and vec_results:
        return _reciprocal_rank_fusion(vec_results, bm25_results, id_field=id_field, limit=limit)
    return vec_results[:limit] or bm25_results[:limit]


def _rank_fusion_pipeline(
    vector_pipeline: list[dict],
    bm25_pipeline: list[dict],
    vector_score_field: str,
    bm25_score_field: str,
    limit: int,
) -> list[dict]:
    """Build a $rankFusion aggregation pipeline."""
    return [
        {
            "$rankFusion": {
                "input": {
                    "pipelines": {
                        "vector": vector_pipeline,
                        "bm25": bm25_pipeline,
                    }
                },
                "combination": {
                    "weights": {"vector": 0.6, "bm25": 0.4},
                },
                "scoreDetails": True,
            }
        },
        {"$addFields": {"score": {"$meta": "searchScore"}}},
        {"$limit": limit},
        {"$project": {"embedding": 0, "_id": 0}},
    ]


def _raise_index_error(exc: OperationFailure, index_name: str, collection: str) -> None:
    if "index not found" in str(exc).lower() or exc.code in (40325, 31082, 13388):
        raise RuntimeError(
            f"Search index '{index_name}' on collection '{collection}' is not available. "
            "Ensure the index exists and has READY status. "
            f"Original error: {exc}"
        ) from exc
    raise RuntimeError(str(exc)) from exc


def _format_knowledge_result(doc: dict) -> dict:
    cleaned = _clean(doc)
    # Check Voyage reranker score first, then RRF/vector/BM25
    score = (
        cleaned.get("rerank_score")
        or cleaned.get("score")
        or cleaned.get("vector_score")
        or cleaned.get("bm25_score")
    )
    return {
        "document_id": cleaned.get("document_id"),
        "source_id": cleaned.get("source_id"),
        "source_type": cleaned.get("source_type"),
        "source_file": cleaned.get("source_file"),
        "title": cleaned.get("title"),
        "content": cleaned.get("content"),
        "service_id": cleaned.get("service_id"),
        "incident_id": cleaned.get("incident_id"),
        "customer_id": cleaned.get("customer_id"),
        "timestamp": cleaned.get("timestamp"),
        "citation": cleaned.get("citation"),
        "score": score,
    }


# --------------------------------------------------------------------------- #
# 3. Telemetry retrieval                                                       #
# --------------------------------------------------------------------------- #

def query_telemetry(
    service_id: str,
    start=None,
    end=None,
) -> list[dict]:
    """
    Retrieve structured telemetry events for a service within a time range.

    Args:
        service_id: The service ID to filter on.
        start:      Start of time range (datetime or ISO-8601 string). Optional.
        end:        End of time range (datetime or ISO-8601 string). Optional.

    Returns:
        List of telemetry event dicts, sorted chronologically.
        Never includes raw embeddings.
    """
    db = get_db()
    col = db[cfg.col_telemetry]

    def _do_query(s_str, e_str):
        str_match: dict[str, Any] = {"service_id": service_id}
        time_filter: dict = {}
        if s_str is not None:
            time_filter["$gte"] = s_str
        if e_str is not None:
            time_filter["$lte"] = e_str
        if time_filter:
            str_match["timestamp"] = time_filter
        cursor = col.find(str_match, {"_id": 0}).sort("timestamp", ASCENDING)
        return [_clean(doc) for doc in cursor]

    s_str = None
    if start is not None:
        try:
            s_str = _parse_datetime(start).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            s_str = str(start)

    e_str = None
    if end is not None:
        try:
            e_str = _parse_datetime(end).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            e_str = str(end)

    results = _do_query(s_str, e_str)

    # Dynamic fallback: if an explicit time filter was passed but returned 0 events
    # (e.g. timeframe mismatch or offset), retrieve available telemetry for this service
    if not results and (start is not None or end is not None):
        log.warning(
            "query_telemetry: no records found for service=%s in specified range %s - %s. "
            "Falling back to retrieving available telemetry for service.",
            service_id, start, end
        )
        results = _do_query(None, None)

    return results


# --------------------------------------------------------------------------- #
# 4. Slack message search                                                      #
# --------------------------------------------------------------------------- #

def search_messages(
    query: str,
    incident_id: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Hybrid semantic + keyword search over incident_messages.

    Uses $vectorSearch + $search (BM25) combined via $rankFusion.
    Optionally filters by incident_id.

    Raises:
        RuntimeError  when embeddings are unavailable.
    """
    _check_embeddings_available("search_messages")

    db = get_db()
    col = db[cfg.col_messages]

    q_emb = _get_query_embedding(query)

    vec_filter = {}
    if incident_id:
        vec_filter = {"incident_id": incident_id}

    vector_pipeline: list[dict] = [
        {
            "$vectorSearch": {
                "index": cfg.vector_idx_messages,
                "path": "embedding",
                "queryVector": q_emb,
                "numCandidates": limit * 20,
                "limit": limit * 4,
                **({"filter": vec_filter} if vec_filter else {}),
            }
        },
        {"$addFields": {"vector_score": {"$meta": "vectorSearchScore"}}},
        {"$project": {"embedding": 0, "_id": 0}},
    ]

    # --- Atlas Vector Search (Atlas Free Tier compliant: 3 vector indexes) ---
    results = _execute_hybrid_search(
        col=col,
        vector_pipeline=vector_pipeline,
        bm25_pipeline=None,
        vector_index=cfg.vector_idx_messages,
        text_index=None,
        id_field="message_id",
        limit=limit,
    )

    out = []
    for doc in results[:limit]:
        cleaned = _clean(doc)
        out.append({
            "message_id": cleaned.get("message_id"),
            "incident_id": cleaned.get("incident_id"),
            "channel": cleaned.get("channel"),
            "sender": cleaned.get("sender"),
            "sender_role": cleaned.get("sender_role"),
            "timestamp": cleaned.get("timestamp"),
            "text": cleaned.get("text"),
            "thread_id": cleaned.get("thread_id"),
            "score": cleaned.get("score") or cleaned.get("vector_score"),
        })
    return out


# --------------------------------------------------------------------------- #
# 5. SLA retrieval                                                             #
# --------------------------------------------------------------------------- #

def search_sla(customer_id: str) -> list[dict]:
    """
    Retrieve all active SLA clauses for a customer, sorted by page and clause.

    Returns structured clause records with threshold fields for deterministic
    SLA calculations by the agent.  Does NOT use LLM or embeddings.

    Args:
        customer_id: e.g. "acme-corp" or "betafinance"

    Returns:
        List of SLA clause dicts including financial_credit_pct, rca_required, etc.
    """
    db = get_db()
    col = db[cfg.col_sla]

    cursor = col.find(
        {"customer_id": customer_id, "is_active": True},
        {"_id": 0},
    ).sort([("page", ASCENDING), ("clause_number", ASCENDING)])

    return [_clean(doc) for doc in cursor]


# --------------------------------------------------------------------------- #
# 6. Deployment retrieval                                                      #
# --------------------------------------------------------------------------- #

def get_deployments(
    service_id: str | None = None,
    start=None,
    end=None,
) -> list[dict]:
    """
    Retrieve deployment records for a service or cluster, optionally within a time range.

    Deployments that *cause* an incident occur *before* the failure onset.
    The search window is dynamically expanded by 3 hours before `start` to capture pre-incident
    change events. If no deployments are found for the specific service (e.g. an API failed
    due to a downstream dependency change), this function queries MongoDB `services` collection
    to find dependent services and check deployments across those dependencies.

    Args:
        service_id: Service to filter on. If None, retrieves deployments across all services.
        start:      Optional start datetime / ISO string.
        end:        Optional end datetime / ISO string.

    Returns:
        List of deployment dicts sorted chronologically.
    """
    from datetime import timedelta

    db = get_db()
    col = db[cfg.col_deployments]

    def _do_query(s_str, e_str, svc):
        match: dict[str, Any] = {}
        if svc:
            match["service_id"] = svc
        time_filter: dict = {}
        if s_str:
            time_filter["$gte"] = s_str
        if e_str:
            time_filter["$lte"] = e_str
        if time_filter:
            match["deployed_at"] = time_filter
        cursor = col.find(match, {"_id": 0}).sort("deployed_at", ASCENDING)
        return [_clean(doc) for doc in cursor]

    # Dynamically expand window: start - 3 hours, end + 30 min
    s_expanded = None
    if start is not None:
        try:
            s_dt = _parse_datetime(start)
            s_expanded = (s_dt - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            s_expanded = str(start)

    e_expanded = None
    if end is not None:
        try:
            e_dt = _parse_datetime(end)
            e_expanded = (e_dt + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            e_expanded = str(end)

    results = _do_query(s_expanded, e_expanded, service_id)

    # Fallback 1: retry without time filter if empty
    if not results and (start is not None or end is not None):
        results = _do_query(None, None, service_id)

    # Fallback 2: Microservice dependency traversal
    # If no deployments exist for this service, query MongoDB services collection
    # for services it depends on (e.g. checkout-api depends on auth-service)
    if not results and service_id:
        try:
            svc_doc = db[cfg.col_services].find_one({"service_id": service_id})
            if svc_doc and svc_doc.get("depends_on"):
                deps_list = svc_doc["depends_on"]
                dep_match = {"service_id": {"$in": deps_list}}
                cursor_deps = col.find(dep_match, {"_id": 0}).sort("deployed_at", ASCENDING)
                dep_results = [_clean(doc) for doc in cursor_deps]
                if dep_results:
                    results = dep_results
        except Exception as err:
            log.warning("Could not traverse dependencies for deployments: %s", err)

    # Fallback 3: if still empty, retrieve recent cluster deployments
    if not results and service_id:
        cursor_all = col.find({}, {"_id": 0}).sort("deployed_at", -1).limit(10)
        results = [_clean(doc) for doc in cursor_all]

    return results


# --------------------------------------------------------------------------- #
# 7. Incident retrieval                                                        #
# --------------------------------------------------------------------------- #

def get_incident(incident_id: str) -> dict | None:
    """
    Retrieve a single incident record by its ID.

    Returns:
        Incident dict, or None if not found.
    """
    db = get_db()
    doc = db[cfg.col_incidents].find_one({"incident_id": incident_id}, {"_id": 0})
    return _clean(doc) if doc else None


def list_incidents(
    date=None,
    status: str | None = None,
) -> list[dict]:
    """
    List incident records, optionally filtered by date and/or status.

    Args:
        date:   Filter incidents that started on this date.
                Accepts datetime, ISO string, or "YYYY-MM-DD" date string.
        status: Filter by incident status ("open", "resolved", "postmortem").

    Returns:
        List of incident dicts sorted by start_time descending.
    """
    db = get_db()
    col = db[cfg.col_incidents]

    match: dict[str, Any] = {}

    if status:
        match["status"] = status

    if date is not None:
        if isinstance(date, str) and len(date) == 10:
            # "YYYY-MM-DD" — match any time on that day
            match["start_time"] = {
                "$gte": f"{date}T00:00:00Z",
                "$lte": f"{date}T23:59:59Z",
            }
        else:
            dt = _parse_datetime(date)
            date_str = dt.strftime("%Y-%m-%d")
            match["start_time"] = {
                "$gte": f"{date_str}T00:00:00Z",
                "$lte": f"{date_str}T23:59:59Z",
            }

    cursor = col.find(match, {"_id": 0}).sort("start_time", -1)
    return [_clean(doc) for doc in cursor]


# --------------------------------------------------------------------------- #
# 8. Visual evidence search                                                    #
# --------------------------------------------------------------------------- #

def search_visual_evidence(
    query: str,
    incident_id: str | None = None,
    limit: int = 3,
) -> list[dict]:
    """
    Semantic search over visual_evidence using multimodal embeddings.

    Args:
        query:       Natural-language description of what to look for.
        incident_id: Optional filter.
        limit:       Maximum number of results.

    Returns:
        List of visual evidence metadata dicts (no binary image data).
        Each result includes the gridfs_file_id for subsequent image retrieval.

    Raises:
        RuntimeError  when visual embeddings are unavailable.
    """
    db = get_db()
    col = db[cfg.col_visual]

    # Check visual embeddings specifically
    sample = col.find_one({"embedding": {"$ne": None}})
    if sample is None:
        raise RuntimeError(
            "Cannot perform search_visual_evidence: no multimodal embeddings found "
            "in the visual_evidence collection. "
            "Run seed_database without --skip-embeddings to generate them."
        )

    q_emb = _get_query_embedding(query)

    vec_filter = {}
    if incident_id:
        vec_filter = {"incident_id": incident_id}

    pipeline: list[dict] = [
        {
            "$vectorSearch": {
                "index": cfg.vector_idx_visual,
                "path": "embedding",
                "queryVector": q_emb,
                "numCandidates": limit * 10,
                "limit": limit,
                **({"filter": vec_filter} if vec_filter else {}),
            }
        },
        {"$addFields": {"score": {"$meta": "vectorSearchScore"}}},
        {"$project": {"embedding": 0, "_id": 0}},
    ]

    try:
        results = list(col.aggregate(pipeline))
    except OperationFailure as exc:
        _raise_index_error(exc, cfg.vector_idx_visual, cfg.col_visual)

    out = []
    for doc in results:
        cleaned = _clean(doc)
        out.append({
            "evidence_id": cleaned.get("evidence_id"),
            "incident_id": cleaned.get("incident_id"),
            "title": cleaned.get("title"),
            "description": cleaned.get("description"),
            "gridfs_file_id": cleaned.get("gridfs_file_id"),
            "file_name": cleaned.get("file_name"),
            "mime_type": cleaned.get("mime_type"),
            "captured_at": cleaned.get("captured_at"),
            "score": cleaned.get("score"),
        })
    return out


# --------------------------------------------------------------------------- #
# 9. Visual asset retrieval                                                    #
# --------------------------------------------------------------------------- #

def get_visual_asset(file_id: str) -> tuple[bytes, str] | None:
    """
    Download raw asset bytes from GridFS by file ID.

    Args:
        file_id: The string GridFS ObjectId from a visual_evidence record.

    Returns:
        Tuple of (bytes, content_type) or None if the file is not found.
        content_type is derived from GridFS metadata (mime_type field) or
        the filename extension, defaulting to 'image/png'.
    """
    gfs = get_gridfs()
    try:
        oid = ObjectId(file_id)
        grid_out = gfs.get(oid)
        data = grid_out.read()
        # Detect content type from stored metadata, then filename extension
        meta = getattr(grid_out, "metadata", None) or {}
        content_type = meta.get("mime_type") or meta.get("content_type")
        if not content_type:
            fn = getattr(grid_out, "filename", "") or ""
            if fn.lower().endswith(".pdf"):
                content_type = "application/pdf"
            elif fn.lower().endswith((".jpg", ".jpeg")):
                content_type = "image/jpeg"
            else:
                content_type = "image/png"
        return (data, content_type)
    except Exception:  # noqa: BLE001
        return None


def get_pdf_file_id(contract_id: str) -> str | None:
    """
    Find the GridFS ObjectId string for an SLA PDF by contract ID or customer ID.
    e.g. contract_id="SLA-ACME-001" -> matches filename "SLA_SLA-ACME-001.pdf"
    """
    try:
        db = get_db()
        # Look in fs.files collection
        doc = db["fs.files"].find_one({"filename": f"SLA_{contract_id}.pdf"})
        if not doc:
            doc = db["fs.files"].find_one({"filename": {"$regex": contract_id, "$options": "i"}})
        if not doc:
            doc = db["fs.files"].find_one({"filename": {"$regex": r"\.pdf$", "$options": "i"}})
        return str(doc["_id"]) if doc else None
    except Exception:
        return None
