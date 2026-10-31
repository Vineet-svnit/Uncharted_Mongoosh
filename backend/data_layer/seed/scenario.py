"""
backend/data_layer/seed/scenario.py
-------------------------------------
Single source of truth for every stable ID, timestamp and numerical
value in the synthetic AegisRCA scenario.

Import from here instead of hardcoding strings elsewhere.
"""

from __future__ import annotations

from datetime import datetime, timezone

# ── Incident ───────────────────────────────────────────────────────────────────
INCIDENT_ID = "INC-2026-10-28-001"
CUSTOMER_ID_ACME = "acme-corp"
CUSTOMER_ID_BETA = "betafinance"

# All times UTC
T_DEPLOY = datetime(2026, 10, 28, 13, 58, 0, tzinfo=timezone.utc)   # PR #812 deployed
T_IMPACT_START = datetime(2026, 10, 28, 14, 2, 0, tzinfo=timezone.utc)
T_INVESTIGATION_START = datetime(2026, 10, 28, 14, 0, 0, tzinfo=timezone.utc)
T_ROLLBACK = datetime(2026, 10, 28, 14, 22, 0, tzinfo=timezone.utc)  # PR #813 deployed
T_RECOVERY = datetime(2026, 10, 28, 14, 25, 0, tzinfo=timezone.utc)
T_INVESTIGATION_END = T_RECOVERY

DOWNTIME_MINUTES = 23  # 14:02 → 14:25

# ── Redis pool change ─────────────────────────────────────────────────────────
REDIS_POOL_BEFORE = 500
REDIS_POOL_AFTER = 50

# ── Traffic figures ───────────────────────────────────────────────────────────
NORMAL_INGRESS_RPS = 1200        # external requests/sec (stable)
RETRY_MULTIPLIER = 15            # internal retries ~15× normal

# ── PR numbers ────────────────────────────────────────────────────────────────
PR_CAUSE = 812
PR_ROLLBACK = 813

# ── Service IDs ───────────────────────────────────────────────────────────────
SERVICES = [
    "api-gateway",
    "checkout-api",
    "auth-service",
    "redis-cluster-east",
    "payment-service",
    "orders-db",
    "notification-service",
    "user-profile-api",
]

TOPOLOGY_VERSION = "prod-2026-10-28"
ENVIRONMENT = "production"

# ── Channels ──────────────────────────────────────────────────────────────────
SLACK_CHANNELS = ["#incidents", "#sre-oncall", "#engineering", "#leadership"]

