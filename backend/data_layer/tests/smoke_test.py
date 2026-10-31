"""
backend/data_layer/tests/smoke_test.py
----------------------------------------
Quick smoke test: connects to MongoDB, checks collections are populated,
and runs one of each retrieval type.

Run:
    python -m data_layer.tests.smoke_test
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from data_layer.config import cfg
from data_layer.mongo import get_db
from data_layer import (
    get_dependency_chain,
    get_deployments,
    get_incident,
    list_incidents,
    query_telemetry,
    search_sla,
)
from data_layer.seed.scenario import INCIDENT_ID


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print("─" * 60)


def ok(label: str, value=None) -> None:
    if value is not None:
        print(f"  ✓ {label}: {value}")
    else:
        print(f"  ✓ {label}")


def fail(label: str, error: str) -> None:
    print(f"  ✗ {label}: {error}")


def main() -> int:
    errors = 0

    section("MongoDB Connection")
    try:
        db = get_db()
        db.client.admin.command("ping")
        ok("Connected to MongoDB")
    except Exception as exc:
        fail("Connection", str(exc))
        return 1

    section("Collection Counts")
    expected_counts = {
        cfg.col_services: 8,
        cfg.col_deployments: 9,
        cfg.col_messages: 50,
        cfg.col_telemetry: 180,
        cfg.col_incidents: 1,
    }
    for col_name, expected in expected_counts.items():
        actual = db[col_name].count_documents({})
        if actual == expected:
            ok(col_name, actual)
        else:
            fail(col_name, f"expected {expected}, got {actual}")
            errors += 1

    section("$graphLookup — checkout-api dependency chain")
    try:
        result = get_dependency_chain("checkout-api")
        dep_ids = {d["service_id"] for d in result["dependencies"]}
        assert "auth-service" in dep_ids, "auth-service missing"
        assert "redis-cluster-east" in dep_ids, "redis-cluster-east missing"
        ok("get_dependency_chain", f"{len(dep_ids)} dependencies found: {sorted(dep_ids)}")
    except Exception as exc:
        fail("get_dependency_chain", str(exc))
        errors += 1

    section("Telemetry query")
    try:
        result = query_telemetry(
            "redis-cluster-east",
            "2026-10-28T14:00:00Z",
            "2026-10-28T14:25:00Z",
        )
        ok("query_telemetry", f"{len(result)} events returned")
        if result:
            ok("First event timestamp", result[0]["timestamp"])
            ok("Last event timestamp", result[-1]["timestamp"])
    except Exception as exc:
        fail("query_telemetry", str(exc))
        errors += 1

    section("SLA retrieval — Acme Corp")
    try:
        result = search_sla("acme-corp")
        clause_32 = next((c for c in result if c["clause_number"] == "3.2"), None)
        ok("search_sla", f"{len(result)} clauses")
        if clause_32:
            ok("Clause 3.2 rca_required", clause_32["rca_required"])
            ok("Clause 3.2 financial_credit_pct", clause_32["financial_credit_pct"])
        else:
            fail("Clause 3.2", "not found")
            errors += 1
    except Exception as exc:
        fail("search_sla", str(exc))
        errors += 1

    section("Deployments")
    try:
        result = get_deployments("auth-service")
        pr_nums = [d["pr_number"] for d in result]
        ok("get_deployments", f"{len(result)} deployments, PRs: {pr_nums}")
        assert 812 in pr_nums, "PR #812 missing"
        assert 813 in pr_nums, "PR #813 missing"
        ok("PR #812 and #813 present")
    except Exception as exc:
        fail("get_deployments", str(exc))
        errors += 1

    section("Incident retrieval")
    try:
        inc = get_incident(INCIDENT_ID)
        ok("get_incident", inc["title"][:50] if inc else "None")
        ok("downtime_minutes", inc.get("downtime_minutes"))
    except Exception as exc:
        fail("get_incident", str(exc))
        errors += 1

    section("Semantic retrieval availability")
    has_emb = db[cfg.col_knowledge].find_one({"embedding": {"$ne": None}}) is not None
    has_vis = db[cfg.col_visual].find_one({"embedding": {"$ne": None}}) is not None

    if has_emb:
        ok("Knowledge embeddings", "AVAILABLE")
    else:
        print("  ⚠  Knowledge embeddings NOT available — semantic search disabled")

    if has_vis:
        ok("Visual embeddings", "AVAILABLE")
    else:
        print("  ⚠  Visual embeddings NOT available — multimodal search disabled")

    section("Summary")
    if errors == 0:
        print("  🟢 All smoke tests passed.")
    else:
        print(f"  🔴 {errors} test(s) failed.")

    return errors


if __name__ == "__main__":
    sys.exit(main())

