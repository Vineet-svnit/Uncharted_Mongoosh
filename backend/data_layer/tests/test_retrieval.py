"""
backend/data_layer/tests/test_retrieval.py
-------------------------------------------
Retrieval function tests (require live MongoDB + seeded data).

Semantic tests are automatically skipped when embeddings are unavailable.

Run:
    pytest backend/data_layer/tests/test_retrieval.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from data_layer import (
    get_dependency_chain,
    get_deployments,
    get_incident,
    list_incidents,
    query_telemetry,
    search_sla,
)
from data_layer.config import cfg
from data_layer.mongo import get_db
from data_layer.seed.scenario import INCIDENT_ID


def _has_embeddings() -> bool:
    try:
        db = get_db()
        return db[cfg.col_knowledge].find_one({"embedding": {"$ne": None}}) is not None
    except Exception:
        return False


def _has_visual_embeddings() -> bool:
    try:
        db = get_db()
        return db[cfg.col_visual].find_one({"embedding": {"$ne": None}}) is not None
    except Exception:
        return False


SKIP_SEMANTIC = pytest.mark.skipif(
    not _has_embeddings(),
    reason="Embeddings not generated (--skip-embeddings mode). Skipping semantic tests.",
)

SKIP_VISUAL = pytest.mark.skipif(
    not _has_visual_embeddings(),
    reason="Multimodal embeddings not generated. Skipping visual retrieval tests.",
)


# ── Graph test ────────────────────────────────────────────────────────────────

class TestGraphLookup:
    def test_dependency_chain_finds_redis(self):
        result = get_dependency_chain("checkout-api")
        assert result["root"]["service_id"] == "checkout-api"
        dep_ids = {d["service_id"] for d in result["dependencies"]}
        assert "auth-service" in dep_ids, "auth-service not in dependencies"
        assert "redis-cluster-east" in dep_ids, "redis-cluster-east not in dependencies"

    def test_dependency_chain_finds_payment(self):
        result = get_dependency_chain("checkout-api")
        dep_ids = {d["service_id"] for d in result["dependencies"]}
        assert "payment-service" in dep_ids

    def test_dependency_chain_invalid_service(self):
        with pytest.raises(ValueError, match="not found"):
            get_dependency_chain("nonexistent-service")

    def test_dependency_depth_field(self):
        result = get_dependency_chain("checkout-api")
        for dep in result["dependencies"]:
            assert "depth" in dep
            assert dep["depth"] >= 0

    def test_no_embedding_in_result(self):
        result = get_dependency_chain("checkout-api")
        for dep in result["dependencies"]:
            assert "embedding" not in dep

    def test_api_gateway_dependencies(self):
        result = get_dependency_chain("api-gateway")
        dep_ids = {d["service_id"] for d in result["dependencies"]}
        assert "checkout-api" in dep_ids
        assert "user-profile-api" in dep_ids


# ── Telemetry tests ───────────────────────────────────────────────────────────

class TestTelemetry:
    def test_redis_telemetry_during_incident(self):
        result = query_telemetry(
            "redis-cluster-east",
            "2026-10-28T14:00:00Z",
            "2026-10-28T14:25:00Z",
        )
        assert len(result) > 0

    def test_telemetry_sorted_chronologically(self):
        result = query_telemetry(
            "redis-cluster-east",
            "2026-10-28T14:00:00Z",
            "2026-10-28T14:25:00Z",
        )
        timestamps = [r["timestamp"] for r in result]
        assert timestamps == sorted(timestamps)

    def test_no_embeddings_in_telemetry(self):
        result = query_telemetry("redis-cluster-east")
        for r in result:
            assert "embedding" not in r

    def test_telemetry_no_raw_objectid(self):
        result = query_telemetry("auth-service")
        for r in result:
            assert "_id" not in r
            for v in r.values():
                assert not str(type(v)) == "<class 'bson.objectid.ObjectId'>"

    def test_accepts_datetime_objects(self):
        from datetime import datetime, timezone
        result = query_telemetry(
            "api-gateway",
            start=datetime(2026, 10, 28, 14, 0, tzinfo=timezone.utc),
            end=datetime(2026, 10, 28, 14, 30, tzinfo=timezone.utc),
        )
        assert isinstance(result, list)


# ── SLA tests ─────────────────────────────────────────────────────────────────

class TestSlaRetrieval:
    def test_acme_sla_returns_clauses(self):
        result = search_sla("acme-corp")
        assert len(result) > 0

    def test_acme_sla_has_threshold_clauses(self):
        result = search_sla("acme-corp")
        threshold_clauses = [c for c in result if c.get("downtime_min_minutes") is not None]
        assert len(threshold_clauses) >= 3

    def test_acme_clause_32_rca_no_credit(self):
        result = search_sla("acme-corp")
        clause_32 = next((c for c in result if c["clause_number"] == "3.2"), None)
        assert clause_32 is not None, "Acme clause 3.2 not found"
        assert clause_32["rca_required"] is True
        assert clause_32["financial_credit_pct"] == 0.0
        assert clause_32["downtime_min_minutes"] == 20
        assert clause_32["downtime_max_minutes"] == 30

    def test_betafinance_sla_returns_clauses(self):
        result = search_sla("betafinance")
        assert len(result) > 0

    def test_betafinance_clause_32_has_10_pct_credit(self):
        result = search_sla("betafinance")
        clause_32 = next((c for c in result if c["clause_number"] == "3.2"), None)
        assert clause_32 is not None
        assert clause_32["financial_credit_pct"] == 10.0

    def test_sla_result_no_objectid(self):
        result = search_sla("acme-corp")
        for clause in result:
            assert "_id" not in clause


# ── Deployment tests ──────────────────────────────────────────────────────────

class TestDeployments:
    def test_get_auth_service_deployments(self):
        result = get_deployments("auth-service")
        assert len(result) >= 2  # DEP-812 and DEP-813

    def test_pr_812_in_deployments(self):
        result = get_deployments("auth-service")
        pr_nums = [d["pr_number"] for d in result]
        assert 812 in pr_nums

    def test_pr_813_rollback_of_812(self):
        result = get_deployments("auth-service")
        dep813 = next((d for d in result if d["pr_number"] == 813), None)
        assert dep813 is not None
        assert dep813["rollback_of"] == "DEP-812"

    def test_deployment_time_range_filter(self):
        result = get_deployments(
            "auth-service",
            start="2026-10-28T13:00:00Z",
            end="2026-10-28T14:00:00Z",
        )
        # PR #812 at 13:58 should be in range
        assert any(d["pr_number"] == 812 for d in result)
        # PR #813 at 14:22 should NOT be in range
        assert not any(d["pr_number"] == 813 for d in result)


# ── Incident tests ────────────────────────────────────────────────────────────

class TestIncidents:
    def test_get_incident_by_id(self):
        result = get_incident(INCIDENT_ID)
        assert result is not None
        assert result["incident_id"] == INCIDENT_ID

    def test_get_nonexistent_incident(self):
        result = get_incident("INC-DOES-NOT-EXIST")
        assert result is None

    def test_list_incidents_by_date(self):
        result = list_incidents(date="2026-10-28")
        assert any(i["incident_id"] == INCIDENT_ID for i in result)

    def test_list_incidents_by_status(self):
        result = list_incidents(status="postmortem")
        assert len(result) >= 1

    def test_incident_no_objectid(self):
        result = get_incident(INCIDENT_ID)
        assert "_id" not in result


# ── Semantic tests (skipped without embeddings) ───────────────────────────────

class TestSemanticRetrieval:
    @SKIP_SEMANTIC
    def test_knowledge_search_redis_exhaustion(self):
        from data_layer import search_knowledge
        result = search_knowledge(
            "Find previous incidents involving Redis connection pool exhaustion"
        )
        assert len(result) > 0
        # At least one result should reference redis or pool
        texts = " ".join(r["content"].lower() for r in result)
        assert "redis" in texts or "pool" in texts

    @SKIP_SEMANTIC
    def test_knowledge_search_pr_812(self):
        from data_layer import search_knowledge
        result = search_knowledge(
            "Find the PR that reduced the Redis connection pool to 50"
        )
        assert len(result) > 0
        # PR #812 should appear
        sources = [r.get("source_id") for r in result]
        assert "PR-812" in sources, f"PR-812 not in top results: {sources}"

    @SKIP_SEMANTIC
    def test_messages_ddos_hypothesis(self):
        from data_layer import search_messages
        result = search_messages(
            "Was the incident caused by a DDoS attack?",
            INCIDENT_ID,
        )
        assert len(result) > 0
        combined = " ".join(r["text"].lower() for r in result)
        assert "ddos" in combined or "traffic" in combined

    @SKIP_VISUAL
    def test_visual_evidence_redis_saturation(self):
        from data_layer import search_visual_evidence
        result = search_visual_evidence(
            "Find screenshots showing Redis connection pool saturation"
        )
        assert len(result) > 0
        assert result[0]["evidence_id"] == "VE-001"

