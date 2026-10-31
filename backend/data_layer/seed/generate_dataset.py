# -*- coding: utf-8 -*-
"""
backend/data_layer/seed/generate_dataset.py
--------------------------------------------
Generates every structured document for the AegisRCA scenario:
  • 8 services
  • 9 deployments
  • 50 Slack messages
  • 180 telemetry events
  • 4 runbooks (as knowledge chunks)
  • 2 SLA contracts (as knowledge chunks + sla_clause records)
  • 2+ historical postmortems (as knowledge chunks)
  • 1 main incident record

Returns plain Python dicts — no MongoDB dependency here.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from .scenario import (
    CUSTOMER_ID_ACME,
    CUSTOMER_ID_BETA,
    DOWNTIME_MINUTES,
    ENVIRONMENT,
    INCIDENT_ID,
    NORMAL_INGRESS_RPS,
    PR_CAUSE,
    PR_ROLLBACK,
    REDIS_POOL_AFTER,
    REDIS_POOL_BEFORE,
    RETRY_MULTIPLIER,
    SERVICES,
    SLACK_CHANNELS,
    T_DEPLOY,
    T_IMPACT_START,
    T_INVESTIGATION_START,
    T_RECOVERY,
    T_ROLLBACK,
    TOPOLOGY_VERSION,
)

RNG = random.Random(42)


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ─────────────────────────────────────────────────────────────────────────────
# 1. SERVICES
# ─────────────────────────────────────────────────────────────────────────────

def generate_services() -> list[dict]:
    raw = [
        {
            "service_id": "api-gateway",
            "name": "API Gateway",
            "service_type": "api",
            "owner_team": "platform-team",
            "criticality": "critical",
            "description": "Edge reverse proxy and load-balancer. Routes all inbound traffic.",
            "depends_on": ["checkout-api", "user-profile-api"],
        },
        {
            "service_id": "checkout-api",
            "name": "Checkout API",
            "service_type": "api",
            "owner_team": "payments-team",
            "criticality": "critical",
            "description": "Handles payment checkout flows; calls Auth and Payment services.",
            "depends_on": ["auth-service", "payment-service"],
        },
        {
            "service_id": "auth-service",
            "name": "Auth Service",
            "service_type": "service",
            "owner_team": "identity-team",
            "criticality": "critical",
            "description": "JWT issuance and validation; uses Redis for session caching.",
            "depends_on": ["redis-cluster-east"],
        },
        {
            "service_id": "redis-cluster-east",
            "name": "Redis Cluster East",
            "service_type": "cache",
            "owner_team": "platform-team",
            "criticality": "critical",
            "description": "In-memory cache and session store for Auth Service.",
            "depends_on": [],
        },
        {
            "service_id": "payment-service",
            "name": "Payment Service",
            "service_type": "service",
            "owner_team": "payments-team",
            "criticality": "critical",
            "description": "Processes payment transactions; writes to Orders DB.",
            "depends_on": ["orders-db"],
        },
        {
            "service_id": "orders-db",
            "name": "Orders DB",
            "service_type": "database",
            "owner_team": "data-team",
            "criticality": "high",
            "description": "PostgreSQL cluster storing order and transaction records.",
            "depends_on": [],
        },
        {
            "service_id": "notification-service",
            "name": "Notification Service",
            "service_type": "service",
            "owner_team": "product-team",
            "criticality": "medium",
            "description": "Sends email/SMS receipts asynchronously; no hard dependency.",
            "depends_on": [],
        },
        {
            "service_id": "user-profile-api",
            "name": "User Profile API",
            "service_type": "api",
            "owner_team": "identity-team",
            "criticality": "high",
            "description": "CRUD for user profile data; delegates auth to Auth Service.",
            "depends_on": ["auth-service"],
        },
    ]
    for svc in raw:
        svc["environment"] = ENVIRONMENT
        svc["topology_version"] = TOPOLOGY_VERSION
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# 2. DEPLOYMENTS
# ─────────────────────────────────────────────────────────────────────────────

def _commit(seed: str) -> str:
    return hashlib.sha1(seed.encode()).hexdigest()[:12]


def generate_deployments() -> list[dict]:
    deps = []

    # PR #812 — the ROOT CAUSE
    deps.append({
        "deployment_id": "DEP-812",
        "pr_number": PR_CAUSE,
        "commit_hash": _commit("PR812-auth-redis-pool"),
        "service_id": "auth-service",
        "deployed_at": _ts(T_DEPLOY),
        "environment": ENVIRONMENT,
        "status": "success",
        "deployed_by": "alice-chen",
        "files_changed": ["config/redis.js", "config/auth.js"],
        "change_description": (
            "Tune Redis connection pool for cost optimisation. "
            "Reduces max connections from 500 to 50."
        ),
        "code_diff": (
            "diff --git a/config/redis.js b/config/redis.js\n"
            "index a1b2c3d..e4f5a6b 100644\n"
            "--- a/config/redis.js\n"
            "+++ b/config/redis.js\n"
            "@@ -44,7 +44,7 @@ module.exports = {\n"
            "   host: process.env.REDIS_HOST,\n"
            "   port: 6379,\n"
            "   db: 0,\n"
            "-  redis_pool_max_connections: 500,\n"
            "+  redis_pool_max_connections: 50,\n"
            "   connect_timeout: 5000,\n"
            "   idle_timeout: 60000,\n"
            " };\n"
        ),
        "previous_config": {"redis_pool_max_connections": REDIS_POOL_BEFORE},
        "updated_config": {"redis_pool_max_connections": REDIS_POOL_AFTER},
        "rollback_of": None,
        "source_file": "GitHub_PR_812.json",
        "citation": {"file_name": "GitHub_PR_812.json",
                     "line_start": 44, "line_end": 48, "page": None},
    })

    # PR #813 — the ROLLBACK
    deps.append({
        "deployment_id": "DEP-813",
        "pr_number": PR_ROLLBACK,
        "commit_hash": _commit("PR813-auth-redis-pool-rollback"),
        "service_id": "auth-service",
        "deployed_at": _ts(T_ROLLBACK),
        "environment": ENVIRONMENT,
        "status": "success",
        "deployed_by": "bob-kim",
        "files_changed": ["config/redis.js"],
        "change_description": (
            "ROLLBACK of PR #812: restore redis_pool_max_connections to 500."
        ),
        "code_diff": (
            "diff --git a/config/redis.js b/config/redis.js\n"
            "index e4f5a6b..a1b2c3d 100644\n"
            "--- a/config/redis.js\n"
            "+++ b/config/redis.js\n"
            "@@ -44,7 +44,7 @@ module.exports = {\n"
            "   host: process.env.REDIS_HOST,\n"
            "   port: 6379,\n"
            "   db: 0,\n"
            "-  redis_pool_max_connections: 50,\n"
            "+  redis_pool_max_connections: 500,\n"
            "   connect_timeout: 5000,\n"
            "   idle_timeout: 60000,\n"
            " };\n"
        ),
        "previous_config": {"redis_pool_max_connections": REDIS_POOL_AFTER},
        "updated_config": {"redis_pool_max_connections": REDIS_POOL_BEFORE},
        "rollback_of": "DEP-812",
        "source_file": "GitHub_PR_813.json",
        "citation": {"file_name": "GitHub_PR_813.json",
                     "line_start": 44, "line_end": 48, "page": None},
    })

    # Unrelated PRs for other services
    unrelated = [
        {
            "pr": 808, "svc": "api-gateway", "dep_id": "DEP-808",
            "desc": "Add request-id header propagation for distributed tracing.",
            "files": ["middleware/request_id.js"],
            "diff": "diff --git a/middleware/request_id.js ...\n+ req.headers['x-request-id'] = uuid();",
            "dt": T_DEPLOY - timedelta(hours=6),
            "by": "carol-santos",
        },
        {
            "pr": 809, "svc": "payment-service", "dep_id": "DEP-809",
            "desc": "Upgrade Stripe SDK from 10.x to 11.x for SCA compliance.",
            "files": ["package.json", "src/stripe_client.js"],
            "diff": "diff ...\n-  \"stripe\": \"^10.4.0\"\n+  \"stripe\": \"^11.0.0\"",
            "dt": T_DEPLOY - timedelta(hours=4),
            "by": "alice-chen",
        },
        {
            "pr": 810, "svc": "notification-service", "dep_id": "DEP-810",
            "desc": "Switch email provider from SendGrid to AWS SES.",
            "files": ["src/email_provider.js", "config/email.js"],
            "diff": "diff ...\n- const sendgrid = require('@sendgrid/mail');\n+ const ses = require('@aws-sdk/client-ses');",
            "dt": T_DEPLOY - timedelta(hours=3),
            "by": "dave-patel",
        },
        {
            "pr": 811, "svc": "user-profile-api", "dep_id": "DEP-811",
            "desc": "Add pagination to GET /users endpoint (max 100 per page).",
            "files": ["routes/users.js"],
            "diff": "diff ...\n+ const page = parseInt(req.query.page) || 1;\n+ const limit = Math.min(parseInt(req.query.limit) || 20, 100);",
            "dt": T_DEPLOY - timedelta(hours=1, minutes=30),
            "by": "carol-santos",
        },
        {
            "pr": 814, "svc": "checkout-api", "dep_id": "DEP-814",
            "desc": "Fix null pointer in cart total calculation when discount code is invalid.",
            "files": ["src/cart.js"],
            "diff": "diff ...\n- const discount = coupon.discount;\n+ const discount = coupon?.discount ?? 0;",
            "dt": T_RECOVERY + timedelta(hours=2),
            "by": "bob-kim",
        },
        {
            "pr": 815, "svc": "orders-db", "dep_id": "DEP-815",
            "desc": "Add composite index on (customer_id, created_at) for order history queries.",
            "files": ["migrations/20261028_order_index.sql"],
            "diff": "diff ...\n+ CREATE INDEX CONCURRENTLY idx_orders_customer_time ON orders(customer_id, created_at DESC);",
            "dt": T_RECOVERY + timedelta(hours=3),
            "by": "dave-patel",
        },
        {
            "pr": 816, "svc": "api-gateway", "dep_id": "DEP-816",
            "desc": "Increase upstream timeout from 30s to 60s to reduce spurious 504s.",
            "files": ["nginx/upstream.conf"],
            "diff": "diff ...\n- proxy_read_timeout 30s;\n+ proxy_read_timeout 60s;",
            "dt": T_RECOVERY + timedelta(hours=4),
            "by": "alice-chen",
        },
    ]

    for u in unrelated:
        deps.append({
            "deployment_id": u["dep_id"],
            "pr_number": u["pr"],
            "commit_hash": _commit(f"PR{u['pr']}-{u['svc']}"),
            "service_id": u["svc"],
            "deployed_at": _ts(u["dt"]),
            "environment": ENVIRONMENT,
            "status": "success",
            "deployed_by": u["by"],
            "files_changed": u["files"],
            "change_description": u["desc"],
            "code_diff": u["diff"],
            "previous_config": {},
            "updated_config": {},
            "rollback_of": None,
            "source_file": f"GitHub_PR_{u['pr']}.json",
            "citation": {"file_name": f"GitHub_PR_{u['pr']}.json",
                         "line_start": None, "line_end": None, "page": None},
        })

    return deps


# ─────────────────────────────────────────────────────────────────────────────
# 3. SLACK MESSAGES
# ─────────────────────────────────────────────────────────────────────────────

_ENGINEERS = [
    ("alice-chen", "SRE Engineer"),
    ("bob-kim", "Backend Developer"),
    ("carol-santos", "DevOps Engineer"),
    ("dave-patel", "Engineering Manager"),
    ("eve-robinson", "SRE Engineer"),
    ("frank-liu", "Backend Developer"),
]


def _msg(idx: int, sender: str, role: str, dt: datetime,
         text: str, channel: str, thread_id: str | None = None) -> dict:
    return {
        "message_id": f"MSG-{idx:04d}",
        "incident_id": INCIDENT_ID,
        "channel": channel,
        "sender": sender,
        "sender_role": role,
        "timestamp": _ts(dt),
        "text": text,
        "thread_id": thread_id,
        "embedding": None,
    }


def generate_slack_messages() -> list[dict]:  # noqa: PLR0915
    msgs = []
    i = 1

    def add(sender, role, dt, text, channel="#incidents", thread=None):
        nonlocal i
        msgs.append(_msg(i, sender, role, dt, text, channel, thread))
        i += 1

    t = T_INVESTIGATION_START  # 14:00

    # Pre-incident — normal traffic observation (13:55 – 13:58)
    add("eve-robinson", "SRE Engineer",
        T_DEPLOY - timedelta(minutes=3),
        "Traffic looks normal, ~1 200 rps across all regions.", "#sre-oncall")
    add("frank-liu", "Backend Developer",
        T_DEPLOY - timedelta(minutes=2),
        "Deploying PR #812 to auth-service — cost optimisation for Redis pool.", "#engineering")
    add("frank-liu", "Backend Developer",
        T_DEPLOY,
        "PR #812 deployed successfully. Commit a1b2c3d on auth-service.", "#engineering")

    # 14:00 — first alerts
    add("alice-chen", "SRE Engineer",
        t,
        "⚠️ Alert firing: checkout-api p99 latency > 2 s. Investigating.", "#incidents")
    add("bob-kim", "Backend Developer",
        t + timedelta(minutes=1),
        "Seeing elevated error rates on checkout-api. Getting 504s from API gateway logs.", "#incidents",
        thread="MSG-0005")
    add("eve-robinson", "SRE Engineer",
        t + timedelta(minutes=1),
        "Paging on-call. checkout-api returning HTTP 504 Gateway Timeout.", "#sre-oncall")

    # 14:02 — pool saturation starts
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=2),
        "Redis connection pool on auth-service is at 98%. Possibly saturated.", "#incidents")
    add("carol-santos", "DevOps Engineer",
        t + timedelta(minutes=2),
        "Confirmed: redis_pool_utilization metric at 100% for auth-service Redis cluster.", "#incidents")
    add("dave-patel", "Engineering Manager",
        t + timedelta(minutes=3),
        "What's the blast radius? Is checkout completely down?", "#incidents")
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=3),
        "Checkout is degraded, roughly 80% of requests are timing out. user-profile-api is also affected.", "#incidents",
        thread="MSG-0010")

    # DDoS hypothesis
    add("bob-kim", "Backend Developer",
        t + timedelta(minutes=4),
        "We are probably being DDoS'd. Traffic from Europe has increased significantly.", "#incidents")
    add("eve-robinson", "SRE Engineer",
        t + timedelta(minutes=4),
        "Checking ingress — external RPS at 1 203. That's within normal range, not a spike.", "#sre-oncall")
    add("carol-santos", "DevOps Engineer",
        t + timedelta(minutes=5),
        "Agreed with eve. Cloudflare dashboard shows no DDoS event. European traffic is flat.", "#incidents",
        thread="MSG-0012")
    add("bob-kim", "Backend Developer",
        t + timedelta(minutes=5),
        "Hmm. Maybe not DDoS then. What else could cause this?", "#incidents",
        thread="MSG-0012")

    # Internal retry spike
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=6),
        "Internal auth retry rate is spiking — 15 × normal baseline. This is amplifying load on Redis.", "#incidents")
    add("dave-patel", "Engineering Manager",
        t + timedelta(minutes=6),
        "Is this correlated with the PR #812 deploy at 13:58?", "#incidents")
    add("frank-liu", "Backend Developer",
        t + timedelta(minutes=7),
        "I deployed PR #812. It was a Redis pool config change — reduced max connections from 500 to 50.", "#incidents")
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=7),
        "That's almost certainly it. Pool of 50 can't handle peak auth load.", "#incidents",
        thread="MSG-0018")
    add("carol-santos", "DevOps Engineer",
        t + timedelta(minutes=8),
        "New connections are being rejected by Redis. Queue filling up, hence timeouts.", "#incidents",
        thread="MSG-0018")

    # Further investigation
    add("bob-kim", "Backend Developer",
        t + timedelta(minutes=8),
        "Can we confirm: redis_pool_max_connections is set to 50 in production right now?", "#sre-oncall")
    add("frank-liu", "Backend Developer",
        t + timedelta(minutes=9),
        "Confirmed. `redis_pool_max_connections = 50` per PR #812. Should be 500.", "#sre-oncall")
    add("eve-robinson", "SRE Engineer",
        t + timedelta(minutes=9),
        "Auth service is queueing connection requests. Pool exhaustion confirmed.", "#sre-oncall")

    # More DDoS debate
    add("bob-kim", "Backend Developer",
        t + timedelta(minutes=11),
        "I still think the traffic spike from Europe contributed. Let's check regional breakdown.", "#incidents")
    add("carol-santos", "DevOps Engineer",
        t + timedelta(minutes=11),
        "EU-WEST traffic: 320 rps. Same as yesterday at this time. Not elevated.", "#sre-oncall",
        thread="MSG-0026")
    add("bob-kim", "Backend Developer",
        t + timedelta(minutes=12),
        "OK fine. The DDoS theory is out. Root cause is the Redis pool regression.", "#incidents",
        thread="MSG-0026")

    # Rollback preparation
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=12),
        "Preparing rollback PR #813 to restore redis_pool_max_connections to 500.", "#incidents")
    add("dave-patel", "Engineering Manager",
        t + timedelta(minutes=13),
        "Approved. Ship the rollback ASAP.", "#incidents")
    add("carol-santos", "DevOps Engineer",
        t + timedelta(minutes=13),
        "Rollback pipeline triggered for auth-service.", "#sre-oncall")
    add("frank-liu", "Backend Developer",
        t + timedelta(minutes=14),
        "PR #813 — rollback — in CI now. ETA ~8 minutes.", "#engineering")
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=14),
        "While rollback deploys: shall we manually patch the config?", "#incidents")
    add("dave-patel", "Engineering Manager",
        t + timedelta(minutes=15),
        "Stick to the rollback. Manual patches can introduce more risk.", "#incidents",
        thread="MSG-0034")

    # Status updates
    add("eve-robinson", "SRE Engineer",
        t + timedelta(minutes=15),
        "Redis pool utilization still at 100%. No change yet.", "#sre-oncall")
    add("bob-kim", "Backend Developer",
        t + timedelta(minutes=16),
        "504 error rate on checkout-api still ~85%. Customers impacted.", "#incidents")
    add("carol-santos", "DevOps Engineer",
        t + timedelta(minutes=17),
        "Notified Acme Corp account team about ongoing incident.", "#incidents")
    add("dave-patel", "Engineering Manager",
        t + timedelta(minutes=18),
        "Please keep the updates coming every 5 minutes until resolved.", "#incidents")
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=18),
        "Rollback build succeeded. Deploying PR #813 to auth-service now.", "#sre-oncall")
    add("frank-liu", "Backend Developer",
        t + timedelta(minutes=19),
        "PR #813 deployment in progress. Watching auth-service restart.", "#engineering")
    add("eve-robinson", "SRE Engineer",
        t + timedelta(minutes=20),
        "auth-service restarting with redis_pool_max_connections=500. Pool clearing.", "#sre-oncall")
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=21),
        "Redis pool utilization dropping — now at 62%. Good signs.", "#incidents")
    add("carol-santos", "DevOps Engineer",
        t + timedelta(minutes=21),
        "Checkout-api 504 rate falling. Seeing improvement.", "#incidents",
        thread="MSG-0042")

    # Recovery
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=22),
        "PR #813 fully deployed at 14:22 UTC. Redis pool at 35% and falling.", "#incidents")
    add("bob-kim", "Backend Developer",
        t + timedelta(minutes=23),
        "Checkout 504 rate down to 5%. Almost back to normal.", "#incidents")
    add("eve-robinson", "SRE Engineer",
        t + timedelta(minutes=24),
        "Redis pool utilization: 18%. Auth service fully recovered.", "#sre-oncall")
    add("dave-patel", "Engineering Manager",
        t + timedelta(minutes=25),
        "🟢 Services restored at 14:25 UTC. Total customer impact: 23 minutes.", "#incidents")
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=25),
        "Incident resolved. Downtime: 14:02–14:25 UTC (23 min). Acme SLA: RCA required, no financial credit.", "#incidents")

    # Post-incident
    add("dave-patel", "Engineering Manager",
        t + timedelta(minutes=26),
        "Scheduling postmortem for tomorrow. Action items: add Redis pool alerts, add config regression CI checks.", "#incidents")
    add("frank-liu", "Backend Developer",
        t + timedelta(minutes=27),
        "Will draft the RCA document. Lessons: always load-test config changes against peak traffic.", "#engineering")
    add("carol-santos", "DevOps Engineer",
        t + timedelta(minutes=28),
        "Adding monitor for redis_pool_utilization > 80% with PagerDuty alert.", "#sre-oncall")
    add("alice-chen", "SRE Engineer",
        t + timedelta(minutes=29),
        "Adding PR review gate: any Redis config change requires SRE sign-off.", "#sre-oncall")

    # Pad to exactly 50 if needed (deterministic filler messages)
    extra_senders = [
        ("eve-robinson", "SRE Engineer", "#sre-oncall"),
        ("bob-kim", "Backend Developer", "#engineering"),
        ("carol-santos", "DevOps Engineer", "#incidents"),
    ]
    extra_texts = [
        "Confirming all services are healthy post-incident. No further anomalies.",
        "Opened ticket to add Redis pool size to deployment checklist.",
        "Updated on-call runbook with Redis pool exhaustion steps.",
        "Sent post-incident summary to stakeholders.",
        "Configured alert: auth_request_failure_count > 500/min triggers P1 page.",
    ]
    filler_idx = 0
    while len(msgs) < 50:
        sender, role, channel = extra_senders[filler_idx % len(extra_senders)]
        text = extra_texts[filler_idx % len(extra_texts)]
        add(sender, role,
            t + timedelta(minutes=29, seconds=10 * (filler_idx + 1)),
            text, channel)
        filler_idx += 1

    assert len(msgs) == 50, f"Expected 50 messages, got {len(msgs)}"
    return msgs


# ─────────────────────────────────────────────────────────────────────────────
# 4. TELEMETRY EVENTS
# ─────────────────────────────────────────────────────────────────────────────

def generate_telemetry() -> list[dict]:  # noqa: PLR0915, PLR0912
    """Generate exactly 180 telemetry records spanning 13:50 – 14:35 UTC."""
    events: list[dict] = []
    idx = 1

    def ev(service_id, dt, event_type, metric_name, value, unit, severity, message,
           record_type="metric", trace_id=None):
        nonlocal idx
        events.append({
            "event_id": f"TEL-{idx:04d}",
            "incident_id": INCIDENT_ID,
            "service_id": service_id,
            "environment": ENVIRONMENT,
            "timestamp": _ts(dt),
            "record_type": record_type,
            "event_type": event_type,
            "metric_name": metric_name,
            "metric_value": float(value) if value is not None else None,
            "unit": unit,
            "severity": severity,
            "message": message,
            "trace_id": trace_id or f"trace-{idx:05d}",
            "source": "synthetic_monitoring",
        })
        idx += 1

    # Helper: baseline window 13:50–13:57 (pre-deploy), 1-min resolution
    def baseline_window():
        for m in range(-10, -1):           # 13:50 to 13:58 (exclusive)
            t = T_DEPLOY + timedelta(minutes=m)

            # Redis pool — healthy
            ev("redis-cluster-east", t, "redis_pool_utilization",
               "redis_pool_utilization", RNG.uniform(12, 18), "percent", "ok",
               f"Redis pool utilization at {RNG.uniform(12,18):.1f}% — normal")

            # Auth healthy
            ev("auth-service", t, "auth_request_latency",
               "auth_p99_latency_ms", RNG.uniform(18, 30), "ms", "ok",
               "Auth p99 latency nominal")

            # External ingress stable
            ev("api-gateway", t, "ingress_rps",
               "ingress_requests_per_second",
               NORMAL_INGRESS_RPS + RNG.randint(-30, 30), "rps", "ok",
               "Ingress traffic nominal")

            # Checkout healthy
            ev("checkout-api", t, "http_504_count",
               "http_504_count", 0, "count", "ok",
               "No 504 errors observed")

    baseline_window()  # 9 minutes × 4 metrics = 36 events

    # Deployment marker at 13:58
    ev("auth-service", T_DEPLOY, "deployment",
       "deployment_event", 0, "event", "ok",
       "PR #812 deployed: redis_pool_max_connections changed 500 to 50",
       record_type="log", trace_id="trace-deploy-812")

    # Post-deploy degradation 13:58 – 14:02
    for sec_offset in [30, 60, 90, 120]:
        t = T_DEPLOY + timedelta(seconds=sec_offset)
        pct = 20 + sec_offset * 0.35   # rising from 20 → ~62%
        ev("redis-cluster-east", t, "redis_pool_utilization",
           "redis_pool_utilization", min(pct, 100), "percent",
           "warning" if pct < 80 else "critical",
           f"Redis pool rising: {min(pct,100):.0f}%")

    # 14:02 — impact start — pool reaches 100%
    for m in range(0, 24):  # 14:02 to 14:25 inclusive, minute resolution
        t = T_IMPACT_START + timedelta(minutes=m)
        recovering = t >= T_ROLLBACK      # 14:22+
        recovered = t >= T_RECOVERY       # 14:25+

        # --- Redis pool utilization ---
        if recovered:
            pool_pct = RNG.uniform(10, 18)
            sev = "ok"
        elif recovering:
            pool_pct = max(10, 100 - (m - 20) * 30)
            sev = "warning" if pool_pct < 60 else "critical"
        else:
            pool_pct = 100.0
            sev = "critical"
        ev("redis-cluster-east", t, "connection_pool_saturation",
           "redis_pool_utilization", pool_pct, "percent", sev,
           f"Auth Redis connection pool at {pool_pct:.0f}%")

        # --- Connection acquisition timeouts ---
        if recovered:
            acq_timeouts = RNG.randint(0, 2)
        elif recovering:
            acq_timeouts = max(0, int(200 - (m - 20) * 60))
        else:
            acq_timeouts = RNG.randint(180, 230)
        ev("auth-service", t, "connection_acquisition_timeout",
           "redis_connection_timeout_count", acq_timeouts, "count",
           "ok" if acq_timeouts < 10 else "critical",
           f"Redis connection acquisition timeouts: {acq_timeouts}")

        # --- Auth request failures ---
        if recovered:
            auth_fail = RNG.randint(0, 5)
        elif recovering:
            auth_fail = max(0, int(850 - (m - 20) * 250))
        else:
            auth_fail = RNG.randint(800, 900)
        ev("auth-service", t, "auth_request_failure",
           "auth_request_failure_count", auth_fail, "count",
           "ok" if auth_fail < 50 else "critical",
           f"Authentication request failures per minute: {auth_fail}")

        # --- Checkout 504 errors ---
        if recovered:
            errs504 = RNG.randint(0, 3)
        elif recovering:
            errs504 = max(0, int(950 - (m - 20) * 280))
        else:
            errs504 = RNG.randint(900, 1000)
        ev("checkout-api", t, "http_504_response",
           "http_504_count", errs504, "count",
           "ok" if errs504 < 20 else "critical",
           f"Checkout API HTTP 504 responses per minute: {errs504}")

        # --- Internal retry rate ---
        normal_retry = 60
        if recovered:
            retry_rate = RNG.randint(55, 75)
        elif recovering:
            retry_rate = max(normal_retry, int(normal_retry * RETRY_MULTIPLIER - (m - 20) * 80))
        else:
            retry_rate = int(normal_retry * RETRY_MULTIPLIER) + RNG.randint(-50, 50)
        ev("auth-service", t, "internal_retry_rate",
           "internal_retry_per_minute", retry_rate, "count",
           "ok" if retry_rate < 200 else "critical",
           f"Internal auth retries per minute: {retry_rate} "
           f"({'~15× baseline' if not recovered and not recovering else 'recovering'})")

        # --- External ingress (remains normal) ---
        ingress = NORMAL_INGRESS_RPS + RNG.randint(-40, 40)
        ev("api-gateway", t, "ingress_rps",
           "ingress_requests_per_second", ingress, "rps", "ok",
           f"External ingress: {ingress} rps — within normal range (DDoS ruled out)")

        # --- Service availability probe ---
        avail = 0.0 if (not recovered and not recovering) else (
            60.0 + (m - 20) * 15 if recovering else 100.0
        )
        avail = max(0, min(100, avail))
        ev("checkout-api", t, "availability_probe",
           "service_availability_pct", avail, "percent",
           "ok" if avail > 95 else ("warning" if avail > 50 else "critical"),
           f"Checkout API availability: {avail:.0f}%")

    # Recovery confirmation at 14:25
    ev("auth-service", T_RECOVERY, "service_recovery",
       "redis_pool_utilization", RNG.uniform(10, 15), "percent", "ok",
       "Auth service fully recovered after PR #813 rollback.",
       record_type="log", trace_id="trace-recovery-813")

    ev("checkout-api", T_RECOVERY, "service_recovery",
       "http_504_count", 0, "count", "ok",
       "Checkout API 504 errors cleared. Incident resolved.",
       record_type="log", trace_id="trace-recovery-813")

    # Post-recovery — 14:26–14:35
    for m in range(1, 11):
        t = T_RECOVERY + timedelta(minutes=m)
        ev("redis-cluster-east", t, "redis_pool_utilization",
           "redis_pool_utilization", RNG.uniform(12, 20), "percent", "ok",
           "Redis pool stable post-recovery")
        ev("api-gateway", t, "ingress_rps",
           "ingress_requests_per_second",
           NORMAL_INGRESS_RPS + RNG.randint(-30, 30), "rps", "ok",
           "Ingress stable post-incident")

    # Pad/trim to exactly 180
    while len(events) < 180:
        t = T_INVESTIGATION_START - timedelta(minutes=len(events))
        ev("api-gateway", t, "ingress_rps",
           "ingress_requests_per_second",
           NORMAL_INGRESS_RPS + RNG.randint(-20, 20), "rps", "ok",
           "Ingress nominal (extended baseline)")

    events = events[:180]

    assert len(events) == 180, f"Expected 180, got {len(events)}"
    return events


# ─────────────────────────────────────────────────────────────────────────────
# 5. RUNBOOKS
# ─────────────────────────────────────────────────────────────────────────────

def generate_runbooks() -> list[dict]:
    """Return 4 runbooks as plain dicts (text will be chunked separately)."""
    return [
        {
            "runbook_id": "RB-001",
            "title": "Redis Connection Pool Exhaustion",
            "service_id": "redis-cluster-east",
            "content": """# Redis Connection Pool Exhaustion

## Description
This runbook covers diagnosis and remediation of Redis connection pool
exhaustion events, where services are unable to acquire connections from
the Redis pool, leading to cascading timeout failures.

## Symptoms
- `redis_pool_utilization` metric at or near 100 %
- `redis_connection_timeout_count` rising sharply
- Downstream services returning HTTP 503 / 504 errors
- Log entries: `Error: connect ETIMEDOUT` or `Redis connection pool exhausted`

## Diagnostic Steps
1. Check `redis_pool_utilization` metric in Grafana. Is it ≥ 90 %?
2. Identify which service owns the pool: check `service_id` tag on the metric.
3. Inspect recent deployments: `GET /api/deployments?service_id=auth-service&limit=5`
4. Check for any configuration change to `redis_pool_max_connections`.
5. Run `redis-cli INFO clients` to see current connected-clients count.
6. Check for connection leaks: look for sessions in `BLOCKED` state.

## Recommended Actions
- If a recent config change reduced `redis_pool_max_connections`, roll back the PR immediately.
- If connections are being leaked, restart the affected service pod.
- If load is genuinely higher than pool capacity, increase the pool size gradually.
- Do NOT set `redis_pool_max_connections` below 200 without load testing.

## Verification Steps
1. Confirm `redis_pool_utilization` drops below 50 %.
2. Confirm downstream HTTP 504 errors stop.
3. Confirm internal retry rate returns to baseline.

## Related Incidents
- INC-2024-03-15-002 — identical pattern on payment-service Redis
- INC-2026-10-28-001 — auth-service pool reduced 500 → 50 by PR #812
""",
        },
        {
            "runbook_id": "RB-002",
            "title": "HTTP 504 Gateway Timeout Investigation",
            "service_id": "checkout-api",
            "content": """# HTTP 504 Gateway Timeout Investigation

## Description
HTTP 504 errors occur when an upstream service does not respond within
the configured timeout window. This runbook covers systematic diagnosis.

## Symptoms
- `http_504_count` metric elevated on checkout-api or api-gateway
- End-user reports of payment failures
- Alert: "Checkout API p99 latency > 2 s"

## Diagnostic Steps
1. Identify the upstream causing the timeout. Check traces for which
   service call is hanging (auth-service, payment-service?).
2. Is the timeout isolated to one pod / AZ, or system-wide?
3. Check `auth_p99_latency_ms` — is Auth Service slow?
4. Check `redis_pool_utilization` — is the Redis pool saturated?
5. Check external ingress RPS — is there an unusual traffic spike?
6. Review recent deployments in the past 2 hours.

## Recommended Actions
- If Auth Service is the bottleneck, follow RB-001 (Redis Pool Exhaustion).
- If Payment Service is the bottleneck, check Orders DB query latency.
- If traffic is genuinely spiking, enable rate limiting on API Gateway.
- If a bad deploy is suspected, follow RB-004 (Safe Service Rollback).

## Verification Steps
1. `http_504_count` returns to zero.
2. checkout-api p99 latency < 300 ms.
3. Confirm all upstream dependencies are healthy.
""",
        },
        {
            "runbook_id": "RB-003",
            "title": "DDoS Attack Verification",
            "service_id": "api-gateway",
            "content": """# DDoS Attack Verification

## Description
When engineers suspect a Distributed Denial of Service (DDoS) attack,
use this runbook to confirm or rule out the hypothesis before escalating.

## Symptoms (genuine DDoS)
- `ingress_requests_per_second` significantly above baseline (> 2×)
- Traffic concentrated from unexpected geographies
- Diverse or spoofed source IPs
- Legitimate users also affected

## Diagnostic Steps
1. Open Grafana → API Gateway dashboard → ingress_rps.
   Compare current vs. 24-hour baseline.
2. Check Cloudflare / WAF dashboard for DDoS detection events.
3. Break down traffic by region and source IP CIDR.
4. Correlate with internal retry amplification:
   - High retries WITHOUT ingress spike → internal failure, NOT DDoS.
5. Check recent deployments — config regressions can mimic DDoS symptoms.

## DDoS Confirmed Actions
- Enable Cloudflare "Under Attack" mode.
- Apply rate limiting rules on API Gateway.
- Notify Security team and escalate to on-call manager.
- Document IP ranges for blocking.

## DDoS Ruled Out
- If `ingress_requests_per_second` is normal (~1 200 rps baseline),
  the issue is internal. Return to RB-001 or RB-002.
- If internal retry rate is elevated, diagnose the root dependency.

## Verification
- Cloudflare reports no attack event.
- ingress_rps returns to baseline without rate-limiting intervention.
- Internal retries are the actual cause of elevated backend load.

## Important Note
High internal retry rates (e.g., 15× normal) can appear as traffic
amplification. Always check `ingress_requests_per_second` (external)
separately from internal service call rates before declaring DDoS.
""",
        },
        {
            "runbook_id": "RB-004",
            "title": "Safe Service Rollback Procedure",
            "service_id": None,
            "content": """# Safe Service Rollback Procedure

## Description
Use this runbook when a recent deployment is confirmed or suspected to
be the root cause of a production incident and must be reverted.

## Prerequisites
- Identify the deployment to roll back (PR number, commit hash).
- Confirm with the Engineering Manager.
- Ensure rollback PR is ready in CI/CD.

## Steps
1. **Confirm rollback target**: `GET /api/deployments?service_id=<service>`
   Identify the PR and commit to revert.
2. **Prepare rollback PR**: Create a PR reverting the problematic commit.
   Use `git revert <commit_hash>` — do NOT manually edit configs.
3. **Fast-track CI**: Label the PR `priority:incident-rollback` to skip
   non-critical CI gates.
4. **Deploy to production**: Trigger the normal deploy pipeline.
   Monitor service metrics during restart.
5. **Validate recovery**:
   - Confirm the reverted config value is in effect.
   - Check that error rates return to baseline.
   - Confirm downstream services recover.
6. **Update incident channel** with rollback status every 2 minutes.

## Post-Rollback
- Add a blocking PR review requirement for the changed config key.
- File a postmortem ticket within 24 hours.
- Update this runbook if any steps were unclear during the incident.

## Timing Reference
- Typical rollback pipeline: 8–12 minutes end to end.
- If faster resolution is needed, consider manual config override ONLY
  with SRE and Engineering Manager approval.

## Example — INC-2026-10-28-001
- Problematic PR: #812 (redis_pool_max_connections: 500 → 50)
- Rollback PR: #813 (restores to 500)
- Time from decision to deploy: ~9 minutes (14:13 → 14:22)
""",
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 6. POSTMORTEMS
# ─────────────────────────────────────────────────────────────────────────────

def generate_postmortems() -> list[dict]:
    return [
        {
            "postmortem_id": "PM-2024-03-15",
            "title": "Redis Connection Pool Exhaustion — Payment Service (2024-03-15)",
            "incident_id": "INC-2024-03-15-002",
            "affected_services": ["payment-service", "redis-cluster-east", "checkout-api"],
            "date": "2024-03-15",
            "content": """# Postmortem: Redis Connection Pool Exhaustion (2024-03-15)

## Incident Summary
On March 15, 2024, payment-service experienced a Redis connection pool
exhaustion event lasting 31 minutes (12:14–12:45 UTC).
Checkout API returned 503 errors during this window.

## Root Cause
A misconfigured connection pool in payment-service limited max connections
to 25 (correct value: 200). This change was introduced in deployment DEP-
2024-03-14-pay-config without a load test.

## Timeline
- 12:05 UTC: payment-service deployed with pool size = 25
- 12:14 UTC: redis_pool_utilization reached 100%
- 12:20 UTC: Checkout API began returning 503 errors
- 12:30 UTC: Root cause identified — connection pool config
- 12:38 UTC: Rollback deployed
- 12:45 UTC: Services recovered

## Symptoms
- redis_pool_utilization at 100% on payment-service Redis
- redis_connection_timeout_count: 180–220 per minute
- checkout-api HTTP 503 error rate: ~75%
- Internal retry rate: 12× baseline

## Remediation
- Restored redis pool_max_connections to 200
- Implemented Grafana alert: redis_pool_utilization > 80%

## Preventive Measures
- Added CI check: pool size changes require SRE approval
- Load-testing requirement added for all DB/cache config changes
- Redis pool alert added to PagerDuty

## Financial Impact
- Customer downtime: 31 minutes
- SLA breach triggered 5% credit for affected enterprise customers
""",
        },
        {
            "postmortem_id": "PM-2025-08-22",
            "title": "Auth Service Timeout Cascade — Configuration Drift (2025-08-22)",
            "incident_id": "INC-2025-08-22-003",
            "affected_services": ["auth-service", "checkout-api", "user-profile-api"],
            "date": "2025-08-22",
            "content": """# Postmortem: Auth Service Timeout Cascade (2025-08-22)

## Incident Summary
On August 22, 2025, auth-service timeouts caused checkout-api and
user-profile-api to degrade for 18 minutes (09:33–09:51 UTC).

## Root Cause
A configuration drift introduced via a Helm chart override set
`connection_timeout_ms` to 100 ms (correct value: 5 000 ms).
Auth service connections to Redis timed out before the pool was
exhausted, causing authentication to fail rapidly.

## Timeline
- 09:20 UTC: Helm chart deployed with incorrect timeout override
- 09:33 UTC: Auth service timeout errors begin
- 09:40 UTC: checkout-api 504 rate at 60%
- 09:45 UTC: Helm override identified and corrected
- 09:51 UTC: Services recovered

## Symptoms
- auth_p99_latency_ms > 5 000 (timeout threshold hit)
- auth_request_failure_count: 500–700 per minute
- checkout-api HTTP 504 errors: ~60% of requests
- Redis pool utilization was NORMAL (35%) — key differentiator

## Key Differentiator from Pool Exhaustion
Unlike pool exhaustion incidents (INC-2024-03-15-002, INC-2026-10-28-001),
the Redis pool was NOT saturated. The issue was at the connection timeout
configuration level, not pool capacity.

## Remediation
- Reverted Helm override
- Added integration test: auth connection must succeed within 3 s

## Preventive Measures
- Added monitoring for auth_p99_latency_ms > 1 000 ms as a warning
- Helm chart drift detection added to CI pipeline
- Runbook RB-002 updated with auth-specific checks
""",
        },
    ]


# ─────────────────────────────────────────────────────────────────────────────
# 7. MAIN INCIDENT
# ─────────────────────────────────────────────────────────────────────────────

def generate_incident() -> dict:
    return {
        "incident_id": INCIDENT_ID,
        "title": "Checkout API 504 Gateway Timeout — Auth Service Redis Pool Exhaustion",
        "environment": ENVIRONMENT,
        "affected_services": [
            "checkout-api", "auth-service", "redis-cluster-east", "user-profile-api",
        ],
        "customer_id": CUSTOMER_ID_ACME,
        "start_time": _ts(T_INVESTIGATION_START),
        "end_time": _ts(T_RECOVERY),
        "customer_impact_start": _ts(T_IMPACT_START),
        "customer_impact_end": _ts(T_RECOVERY),
        "downtime_minutes": DOWNTIME_MINUTES,
        "status": "postmortem",
        "severity": "P1",
        "root_cause_summary": (
            "PR #812 reduced redis_pool_max_connections from 500 to 50 on auth-service. "
            "Pool exhaustion caused authentication timeouts, which cascaded to checkout-api "
            "504 errors. Rolled back via PR #813 at 14:22 UTC. Recovery by 14:25 UTC."
        ),
        "resolved_at": _ts(T_RECOVERY),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. SLA CONTRACTS (raw data for PDF generation + sla_clauses records)
# ─────────────────────────────────────────────────────────────────────────────

def generate_sla_data() -> list[dict]:
    """
    Returns a list of SLA contract definitions (not yet PDFs or clause records).
    Each dict has `contract_id`, `customer_id`, `customer_name`, `version`,
    `covered_services`, and `clauses` (list of clause dicts).
    """
    return [
        {
            "contract_id": "SLA-ACME-2026",
            "customer_id": CUSTOMER_ID_ACME,
            "customer_name": "Acme Corp",
            "contract_version": "v3.1",
            "effective_date": "2026-01-01",
            "expiry_date": "2026-12-31",
            "covered_services": [
                "checkout-api", "auth-service", "payment-service",
                "api-gateway", "user-profile-api",
            ],
            "availability_commitment_pct": 99.9,
            "clauses": [
                {
                    "clause_number": "1",
                    "title": "Availability Commitment",
                    "content": (
                        "Provider guarantees 99.9% monthly uptime for all Covered Services. "
                        "Uptime is measured as the percentage of minutes in a calendar month "
                        "during which the Covered Services are available and operational."
                    ),
                    "downtime_min_minutes": None,
                    "downtime_max_minutes": None,
                    "financial_credit_pct": None,
                    "rca_required": None,
                    "page": 1,
                },
                {
                    "clause_number": "2",
                    "title": "Downtime Definition",
                    "content": (
                        "\"Downtime\" is defined as any period during which the Covered "
                        "Services return HTTP 5xx errors for more than 5% of requests "
                        "sustained for more than two (2) consecutive minutes, as measured "
                        "by Provider's monitoring systems."
                    ),
                    "downtime_min_minutes": None,
                    "downtime_max_minutes": None,
                    "financial_credit_pct": None,
                    "rca_required": None,
                    "page": 1,
                },
                {
                    "clause_number": "3.1",
                    "title": "SLA Credit — Minor Incident (less than 20 minutes)",
                    "content": (
                        "If cumulative Downtime in a calendar month is less than twenty (20) "
                        "minutes, no service credit shall be issued. Provider will investigate "
                        "internally and document findings."
                    ),
                    "downtime_min_minutes": 0,
                    "downtime_max_minutes": 20,
                    "financial_credit_pct": 0.0,
                    "rca_required": False,
                    "page": 2,
                },
                {
                    "clause_number": "3.2",
                    "title": "SLA Credit — Moderate Incident (20 to less than 30 minutes)",
                    "content": (
                        "If cumulative Downtime in a calendar month is twenty (20) minutes "
                        "or more but less than thirty (30) minutes, Provider shall deliver a "
                        "formal Root Cause Analysis (RCA) document to Customer within five (5) "
                        "business days. No financial credit shall be applied."
                    ),
                    "downtime_min_minutes": 20,
                    "downtime_max_minutes": 30,
                    "financial_credit_pct": 0.0,
                    "rca_required": True,
                    "page": 2,
                },
                {
                    "clause_number": "3.3",
                    "title": "SLA Credit — Major Incident (30 minutes or more)",
                    "content": (
                        "If cumulative Downtime in a calendar month is thirty (30) minutes "
                        "or more, Provider shall apply a service credit of five percent (5%) "
                        "of the monthly service fee for the affected billing period, in addition "
                        "to the RCA requirement specified in clause 3.2."
                    ),
                    "downtime_min_minutes": 30,
                    "downtime_max_minutes": None,
                    "financial_credit_pct": 5.0,
                    "rca_required": True,
                    "page": 2,
                },
                {
                    "clause_number": "4",
                    "title": "Exclusions",
                    "content": (
                        "SLA credits do not apply to Downtime caused by: (a) Customer's own "
                        "systems or third-party services not operated by Provider; (b) Force "
                        "majeure events; (c) Scheduled maintenance windows communicated at "
                        "least 72 hours in advance; (d) Customer-requested configuration "
                        "changes that have not been reviewed by Provider's SRE team."
                    ),
                    "downtime_min_minutes": None,
                    "downtime_max_minutes": None,
                    "financial_credit_pct": None,
                    "rca_required": None,
                    "page": 3,
                },
                {
                    "clause_number": "5",
                    "title": "RCA Reporting Requirements",
                    "content": (
                        "For incidents requiring a formal Root Cause Analysis (see clause 3.2 "
                        "and 3.3), the RCA document must include: (a) Incident timeline; "
                        "(b) Root cause identification; (c) Customer impact summary; "
                        "(d) Corrective actions taken; (e) Preventive measures planned. "
                        "RCA must be delivered within five (5) business days of incident "
                        "resolution."
                    ),
                    "downtime_min_minutes": None,
                    "downtime_max_minutes": None,
                    "financial_credit_pct": None,
                    "rca_required": None,
                    "page": 3,
                },
            ],
        },
        {
            "contract_id": "SLA-BETAFIN-2026",
            "customer_id": CUSTOMER_ID_BETA,
            "customer_name": "BetaFinance Ltd",
            "contract_version": "v1.0",
            "effective_date": "2026-06-01",
            "expiry_date": "2027-05-31",
            "covered_services": ["checkout-api", "payment-service", "api-gateway"],
            "availability_commitment_pct": 99.95,
            "clauses": [
                {
                    "clause_number": "1",
                    "title": "Availability Commitment",
                    "content": (
                        "Provider guarantees 99.95% monthly uptime for all Covered Services. "
                        "This represents a maximum of 21.9 minutes of permitted Downtime per month."
                    ),
                    "downtime_min_minutes": None,
                    "downtime_max_minutes": None,
                    "financial_credit_pct": None,
                    "rca_required": None,
                    "page": 1,
                },
                {
                    "clause_number": "2",
                    "title": "Downtime Definition",
                    "content": (
                        "\"Downtime\" means any period during which the Covered Services "
                        "return error rates exceeding two percent (2%) of total requests "
                        "for any period of sixty (60) or more consecutive seconds."
                    ),
                    "downtime_min_minutes": None,
                    "downtime_max_minutes": None,
                    "financial_credit_pct": None,
                    "rca_required": None,
                    "page": 1,
                },
                {
                    "clause_number": "3.1",
                    "title": "SLA Credit — Tier 1 (less than 15 minutes)",
                    "content": (
                        "For Downtime of less than fifteen (15) minutes, no service credit "
                        "is issued. Provider shall notify Customer within one (1) hour of "
                        "incident resolution."
                    ),
                    "downtime_min_minutes": 0,
                    "downtime_max_minutes": 15,
                    "financial_credit_pct": 0.0,
                    "rca_required": False,
                    "page": 2,
                },
                {
                    "clause_number": "3.2",
                    "title": "SLA Credit — Tier 2 (15 to less than 60 minutes)",
                    "content": (
                        "For Downtime of fifteen (15) minutes or more but less than sixty "
                        "(60) minutes, Provider shall apply a service credit of ten percent "
                        "(10%) of the monthly service fee and deliver a formal RCA within "
                        "three (3) business days."
                    ),
                    "downtime_min_minutes": 15,
                    "downtime_max_minutes": 60,
                    "financial_credit_pct": 10.0,
                    "rca_required": True,
                    "page": 2,
                },
                {
                    "clause_number": "3.3",
                    "title": "SLA Credit — Tier 3 (60 minutes or more)",
                    "content": (
                        "For Downtime of sixty (60) minutes or more, Provider shall apply "
                        "a service credit of twenty-five percent (25%) of the monthly service "
                        "fee and deliver a formal RCA within one (1) business day."
                    ),
                    "downtime_min_minutes": 60,
                    "downtime_max_minutes": None,
                    "financial_credit_pct": 25.0,
                    "rca_required": True,
                    "page": 3,
                },
                {
                    "clause_number": "4",
                    "title": "Exclusions",
                    "content": (
                        "This SLA does not apply to: (a) Downtime resulting from Customer "
                        "API misuse; (b) Scheduled maintenance windows; (c) Third-party "
                        "payment network outages outside Provider's control; "
                        "(d) Beta or preview features."
                    ),
                    "downtime_min_minutes": None,
                    "downtime_max_minutes": None,
                    "financial_credit_pct": None,
                    "rca_required": None,
                    "page": 3,
                },
            ],
        },
    ]
