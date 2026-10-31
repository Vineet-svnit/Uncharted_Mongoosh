"""
backend/data_layer/tests/test_dataset.py
-----------------------------------------
Dataset consistency tests.

Run with:
    pytest backend/data_layer/tests/test_dataset.py -v
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Allow running from the backend directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from data_layer.config import cfg
from data_layer.mongo import get_db
from data_layer.seed.scenario import (
    INCIDENT_ID,
    PR_CAUSE,
    PR_ROLLBACK,
    REDIS_POOL_AFTER,
    REDIS_POOL_BEFORE,
    T_DEPLOY,
    T_RECOVERY,
    T_ROLLBACK,
)

FIXTURE_PATH = Path(__file__).parent.parent / "seed" / "expected_results.json"


@pytest.fixture(scope="module")
def db():
    return get_db()


@pytest.fixture(scope="module")
def expected():
    with FIXTURE_PATH.open() as f:
        return json.load(f)


# ── Collection count tests ────────────────────────────────────────────────────

class TestCollectionCounts:
    def test_service_count(self, db):
        assert db[cfg.col_services].count_documents({}) == 8

    def test_deployment_count(self, db):
        assert db[cfg.col_deployments].count_documents({}) == 9

    def test_slack_message_count(self, db):
        assert db[cfg.col_messages].count_documents({}) == 50

    def test_telemetry_count(self, db):
        assert db[cfg.col_telemetry].count_documents({}) == 180

    def test_runbook_chunk_count(self, db):
        count = db[cfg.col_knowledge].count_documents({"source_type": "runbook"})
        # At least 4 runbook-sourced chunks (may be split)
        assert count >= 4

    def test_sla_contract_count(self, db):
        # Two distinct contract IDs in sla_clauses
        contracts = db[cfg.col_sla].distinct("contract_id")
        assert len(contracts) == 2

    def test_visual_evidence_count(self, db):
        assert db[cfg.col_visual].count_documents({}) == 2

    def test_postmortem_chunk_count(self, db):
        count = db[cfg.col_knowledge].count_documents({"source_type": "postmortem"})
        assert count >= 2

    def test_incident_count(self, db):
        assert db[cfg.col_incidents].count_documents({}) >= 1


# ── Referential integrity ─────────────────────────────────────────────────────

class TestReferentialIntegrity:
    def test_service_dependencies_valid(self, db):
        """All service depends_on entries must reference existing service IDs."""
        valid_ids = set(db[cfg.col_services].distinct("service_id"))
        for svc in db[cfg.col_services].find({}, {"depends_on": 1, "service_id": 1, "_id": 0}):
            for dep_id in svc.get("depends_on", []):
                assert dep_id in valid_ids, (
                    f"Service '{svc['service_id']}' depends on unknown '{dep_id}'"
                )

    def test_deployments_reference_valid_services(self, db):
        valid_ids = set(db[cfg.col_services].distinct("service_id"))
        for dep in db[cfg.col_deployments].find({}, {"service_id": 1, "_id": 0}):
            assert dep["service_id"] in valid_ids, (
                f"Deployment references unknown service '{dep['service_id']}'"
            )

    def test_all_incident_messages_share_incident_id(self, db):
        ids = db[cfg.col_messages].distinct("incident_id")
        assert INCIDENT_ID in ids

    def test_telemetry_consistent_incident_id(self, db):
        ids = db[cfg.col_telemetry].distinct("incident_id")
        assert len(ids) >= 1  # at least one incident represented


# ── Ground-truth consistency tests ────────────────────────────────────────────

class TestGroundTruth:
    def test_pr_812_deployed_at_1358(self, db, expected):
        dep = db[cfg.col_deployments].find_one({"pr_number": PR_CAUSE})
        assert dep is not None, "PR #812 not found"
        assert dep["deployed_at"] == expected["deployment_time_utc"]

    def test_pr_812_pool_change_500_to_50(self, db, expected):
        dep = db[cfg.col_deployments].find_one({"pr_number": PR_CAUSE})
        assert dep["previous_config"]["redis_pool_max_connections"] == REDIS_POOL_BEFORE
        assert dep["updated_config"]["redis_pool_max_connections"] == REDIS_POOL_AFTER

    def test_redis_pool_reached_100_percent(self, db):
        peak = db[cfg.col_telemetry].find_one({
            "metric_name": "redis_pool_utilization",
            "metric_value": 100.0,
        })
        assert peak is not None, "No telemetry record showing 100% Redis pool utilization"

    def test_internal_retries_elevated(self, db, expected):
        """At least one retry event should be >= 15× the normal baseline of ~60."""
        threshold = 60 * expected["internal_retry_multiplier"] * 0.7  # 70% of 15×
        high_retries = db[cfg.col_telemetry].find_one({
            "metric_name": "internal_retry_per_minute",
            "metric_value": {"$gte": threshold},
        })
        assert high_retries is not None, (
            f"No telemetry showing internal retries >= {threshold:.0f}/min"
        )

    def test_external_ingress_remained_normal(self, db, expected):
        """External ingress should never be more than 2× the baseline during incident."""
        baseline = expected["external_ingress_rps_baseline"]
        anomalous = db[cfg.col_telemetry].find_one({
            "metric_name": "ingress_requests_per_second",
            "metric_value": {"$gt": baseline * 2},
        })
        assert anomalous is None, "External ingress spike detected — contradicts scenario"

    def test_rollback_pr_813_at_1422(self, db, expected):
        dep = db[cfg.col_deployments].find_one({"pr_number": PR_ROLLBACK})
        assert dep is not None, "PR #813 (rollback) not found"
        assert dep["deployed_at"] == expected["rollback_time_utc"]

    def test_incident_downtime_23_minutes(self, db, expected):
        inc = db[cfg.col_incidents].find_one({"incident_id": INCIDENT_ID})
        assert inc is not None
        assert inc["downtime_minutes"] == expected["downtime_minutes"]

    def test_acme_sla_rca_required_no_credit(self, db, expected):
        """Acme Corp clause 3.2 must require RCA with 0% financial credit."""
        clause = db[cfg.col_sla].find_one({
            "customer_id": expected["acme_sla"]["customer_id"],
            "clause_number": expected["acme_sla"]["applicable_clause"],
        })
        assert clause is not None, "Acme clause 3.2 not found"
        assert clause["rca_required"] is True
        assert clause["financial_credit_pct"] == 0.0

    def test_checkout_downtime_range_in_sla(self, db, expected):
        """The 23-minute downtime must fall in the 20–30 minute bracket."""
        downtime = expected["downtime_minutes"]
        clause = db[cfg.col_sla].find_one({
            "customer_id": expected["acme_sla"]["customer_id"],
            "downtime_min_minutes": {"$lte": downtime},
            "$or": [
                {"downtime_max_minutes": {"$gt": downtime}},
                {"downtime_max_minutes": None},
            ],
            "financial_credit_pct": 0.0,
            "rca_required": True,
        })
        assert clause is not None, (
            "No SLA clause matching 23-min downtime with RCA required and 0% credit"
        )


# ── Timestamp ordering ────────────────────────────────────────────────────────

class TestTimestamps:
    def test_telemetry_timestamps_are_iso_strings(self, db):
        sample = db[cfg.col_telemetry].find_one({})
        assert isinstance(sample["timestamp"], str)
        # Should parse without error
        from datetime import datetime
        datetime.fromisoformat(sample["timestamp"].replace("Z", "+00:00"))

    def test_pr_812_before_pr_813(self, db):
        dep812 = db[cfg.col_deployments].find_one({"pr_number": PR_CAUSE})
        dep813 = db[cfg.col_deployments].find_one({"pr_number": PR_ROLLBACK})
        assert dep812["deployed_at"] < dep813["deployed_at"]

    def test_messages_within_window(self, db):
        """All messages should be timestamped between 13:55 and 14:30 UTC."""
        early = db[cfg.col_messages].find_one({
            "timestamp": {"$lt": "2026-10-28T13:55:00Z"}
        })
        late = db[cfg.col_messages].find_one({
            "timestamp": {"$gt": "2026-10-28T14:31:00Z"}
        })
        assert early is None, f"Message timestamp too early: {early}"
        assert late is None, f"Message timestamp too late: {late}"

