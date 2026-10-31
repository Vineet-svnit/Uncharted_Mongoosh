import { Thread, ChatMessage } from "@/types/chat";
import { InvestigationResult } from "@/types/investigation";

export const MOCK_INVESTIGATION_RESULT: InvestigationResult = {
  investigation_status: "completed",
  incident_id: "INC-2026-10-28-001",
  summary:
    "Checkout API experienced high rates of HTTP 504 Gateway Timeouts between 14:00 and 14:25 UTC due to Redis connection pool exhaustion following PR #812 deployed to Auth Service at 13:58 UTC. A rollback at 14:24 UTC restored normal operations.",
  root_cause: {
    title: "Redis Connection Pool Configuration Regression",
    explanation:
      "PR #812 reduced the maximum Redis connection pool size from 500 to 50 in Auth Service under high concurrency. During peak traffic at 14:00 UTC, the pool saturated immediately at 100%, causing cascading auth timeouts and triggering 15x retry amplification back to Checkout API.",
    status: "likely",
    confidence: "High",
  },
  affected_services: [
    {
      service_id: "checkout-api",
      impact: "Spike to 92% HTTP 504 Gateway Timeouts; customer cart checkout blocked",
      type: "failing",
    },
    {
      service_id: "auth-service",
      impact: "JWT token validation latency escalated from 12ms to 4,800ms; internal retries surged 15x",
      type: "root_cause",
    },
    {
      service_id: "redis-cluster-east",
      impact: "Connection pool utilization hit 100% capacity (50/50 pool connections exhausted)",
      type: "impacted",
    },
    {
      service_id: "payment-gateway",
      impact: "Normal status (unaffected; blocked prior at checkout tier)",
      type: "normal",
    },
  ],
  timeline: [
    {
      timestamp: "2026-10-28T13:58:00Z",
      title: "PR #812 Deployed to Auth Service",
      description:
        "Auth Service release v2.4.1 deployed. Commit 9b4d8a changed default pool size from 500 to 50 connections.",
      evidence_ids: ["EVD-001"],
    },
    {
      timestamp: "2026-10-28T14:01:00Z",
      title: "Redis Pool Reaches 100% Saturation",
      description:
        "Active connections pegged at 50/50 max pool limit. Queue latency spiked from 1.2ms to 3,400ms.",
      evidence_ids: ["EVD-002"],
    },
    {
      timestamp: "2026-10-28T14:04:00Z",
      title: "Auth Requests Timeout & Checkout 504 Errors Surge",
      description:
        "Checkout API failed to validate session tokens within 5s timeout; error rates spiked to 92%.",
      evidence_ids: ["EVD-002"],
    },
    {
      timestamp: "2026-10-28T14:10:00Z",
      title: "DDoS Hypothesis Raised in War Room",
      description:
        "Slack discussion in #incident-checkout suspected external botnet or volumetric DDoS due to error volume.",
      evidence_ids: ["EVD-005"],
    },
    {
      timestamp: "2026-10-28T14:18:00Z",
      title: "Telemetry Cross-Examination Debunks DDoS",
      description:
        "Ingress edge traffic verified flat at 1,210 rps. Telemetry revealed internal retries amplified 15x instead.",
      evidence_ids: ["EVD-004"],
    },
    {
      timestamp: "2026-10-28T14:24:00Z",
      title: "Emergency Rollback Deployed (PR #813)",
      description:
        "Reverted connection pool setting to 500 max connections. Connection pool saturation cleared instantly.",
      evidence_ids: ["EVD-003"],
    },
    {
      timestamp: "2026-10-28T14:25:00Z",
      title: "Full Recovery Confirmed",
      description:
        "HTTP 504 error rate dropped below 0.01% baseline; auth token validation latency returned to 11ms.",
      evidence_ids: ["EVD-002"],
    },
  ],
  supporting_evidence: [
    {
      evidence_id: "EVD-001",
      source_type: "deployment_pr",
      source_id: "GitHub PR #812",
      title: "Auth Service Redis connection pool config refactor",
      content:
        "PR #812: 'Clean up unused connection pool options and adjust default sizing'. Changed redis.pool.max_size = 50 from previous 500 in auth-service/src/config.ts line 44.",
      service_id: "auth-service",
      timestamp: "2026-10-28T13:58:00Z",
      citation: {
        file_name: "auth-service/src/config.ts",
        line_start: 44,
        line_end: 48,
        page: null,
      },
      retrieval_method: "find_recent_deployments",
      relevance_score: 0.98,
      classification: "supporting",
    },
    {
      evidence_id: "EVD-002",
      source_type: "telemetry",
      source_id: "Grafana-Redis-Dashboard-04",
      title: "Redis Pool Utilization & 504 Error Rate Metrics",
      content:
        "Time-series telemetry shows Redis pool saturation reaching exactly 50 connections (100%) at 14:01:12 UTC. Correlates 1:1 with Checkout API 504 gateway timeouts rising from 0.02% to 92.4%.",
      service_id: "redis-cluster-east",
      timestamp: "2026-10-28T14:01:00Z",
      citation: {
        file_name: "dashboards/redis-cluster-east.json",
        line_start: 112,
        line_end: 145,
      },
      retrieval_method: "query_service_telemetry",
      relevance_score: 0.95,
      classification: "supporting",
      asset_file_id: "gridfs_redis_001",
    },
    {
      evidence_id: "EVD-003",
      source_type: "deployment_pr",
      source_id: "GitHub PR #813",
      title: "Emergency Hotfix: Restore Redis pool max_size = 500",
      content:
        "PR #813 emergency rollback deployed at 14:24 UTC. Reinstated max_size = 500. Immediate drop in queue depth and connection contention.",
      service_id: "auth-service",
      timestamp: "2026-10-28T14:24:00Z",
      citation: {
        file_name: "auth-service/src/config.ts",
        line_start: 44,
        line_end: 48,
      },
      retrieval_method: "find_recent_deployments",
      relevance_score: 0.94,
      classification: "supporting",
    },
  ],
  contradicting_evidence: [
    {
      evidence_id: "EVD-004",
      source_type: "telemetry",
      source_id: "Cloudflare-Edge-Ingress-104",
      title: "Edge Ingress Traffic Volume vs Suspected External DDoS",
      content:
        "Initial Slack hypothesis claimed an external volumetric DDoS attack. However, Cloudflare edge ingress telemetry demonstrated completely steady ingress at 1,210 RPS (±4%). In contrast, internal service-to-service retries increased 15x due to unthrottled retry loops, creating an internal retry storm.",
      service_id: "checkout-api",
      timestamp: "2026-10-28T14:10:00Z",
      citation: {
        file_name: "edge-traffic/ingress-timeseries-20261028.json",
        line_start: 24,
        line_end: 50,
      },
      retrieval_method: "query_service_telemetry",
      relevance_score: 0.91,
      classification: "contradicting",
    },
    {
      evidence_id: "EVD-005",
      source_type: "slack_message",
      source_id: "Slack #incident-checkout message #104",
      title: "War Room Chat Hypothesis: 'We are taking heavy bot traffic / DDoS'",
      content:
        "SRE On-Call at 14:10 UTC: 'Seeing 90% errors on Checkout. Could this be the botnet DDoS targeted at payment endpoints?' Contradicted by network ingress metrics which confirm no unusual external volumetric surge.",
      service_id: "checkout-api",
      timestamp: "2026-10-28T14:10:00Z",
      citation: {
        file_name: "slack-archive/incident-checkout-20261028.txt",
        line_start: 104,
        line_end: 110,
      },
      retrieval_method: "search_incident_messages",
      relevance_score: 0.82,
      classification: "contradicting",
    },
  ],
  sla_assessment: {
    status: "assessed",
    customer_id: "Acme Corp",
    downtime_minutes: 23,
    rca_required: true,
    credit_percent: 0.0,
    explanation:
      "Under Section 4.2 of the Master Services Agreement for Acme Corp, cumulative monthly downtime between 20 and 30 minutes requires delivery of a formal Root Cause Analysis (RCA) within 5 business days. Financial service credit penalty is 0% (financial credits only trigger above 60 minutes cumulative downtime at 5%).",
  },
  recommendations: [
    "Restore and enforce a strict minimum Redis connection pool size of 500 in auth-service configuration.",
    "Implement connection pool saturation alerts triggering at 80% pool utilization threshold.",
    "Introduce circuit breaking and exponential backoff retry policies with jitter between Checkout API and Auth Service to avoid retry storms.",
    "Establish automated integration load tests in staging to catch connection-pool size regressions prior to production deployment.",
  ],
  missing_evidence: [],
  citations: [
    {
      evidence_id: "EVD-001",
      source_type: "deployment_pr",
      source_id: "GitHub PR #812",
      title: "Auth Service Redis connection pool config refactor",
      citation: {
        file_name: "auth-service/src/config.ts",
        line_start: 44,
        line_end: 48,
      },
    },
    {
      evidence_id: "EVD-002",
      source_type: "telemetry",
      source_id: "Grafana-Redis-Dashboard-04",
      title: "Redis Pool Utilization & 504 Error Rate Metrics",
      citation: {
        file_name: "dashboards/redis-cluster-east.json",
        line_start: 112,
        line_end: 145,
      },
    },
    {
      evidence_id: "EVD-004",
      source_type: "telemetry",
      source_id: "Cloudflare-Edge-Ingress-104",
      title: "Edge Ingress Traffic Volume vs Suspected External DDoS",
      citation: {
        file_name: "edge-traffic/ingress-timeseries-20261028.json",
        line_start: 24,
        line_end: 50,
      },
    },
  ],
  service_graph: {
    nodes: [
      {
        id: "checkout-api",
        label: "Checkout API",
        status: "failing",
        metrics: { "Error Rate": "92.4%", "Status": "504 Gateway Timeout" },
      },
      {
        id: "auth-service",
        label: "Auth Service",
        status: "root_cause",
        metrics: { "Latency p99": "4,800ms", "Retries": "15x" },
      },
      {
        id: "redis-cluster-east",
        label: "Redis Cluster (East)",
        status: "impacted",
        metrics: { "Pool Capacity": "100% (50/50)", "Wait Queue": "420 req" },
      },
      {
        id: "payment-gateway",
        label: "Payment Gateway",
        status: "healthy",
        metrics: { "Status": "200 OK", "Load": "Normal" },
      },
    ],
    edges: [
      { from: "checkout-api", to: "auth-service", label: "JWT Verify (HTTP)" },
      { from: "auth-service", to: "redis-cluster-east", label: "Session Cache (TCP:6379)" },
      { from: "checkout-api", to: "payment-gateway", label: "Process Charge" },
    ],
  },
  telemetry_series: [
    { timestamp: "13:55", redis_utilization: 12, checkout_504_pct: 0.01, ingress_rps: 1205, internal_retries: 1.0 },
    { timestamp: "13:58", redis_utilization: 15, checkout_504_pct: 0.02, ingress_rps: 1210, internal_retries: 1.1 },
    { timestamp: "14:00", redis_utilization: 82, checkout_504_pct: 14.5, ingress_rps: 1215, internal_retries: 3.4 },
    { timestamp: "14:02", redis_utilization: 100, checkout_504_pct: 92.4, ingress_rps: 1210, internal_retries: 15.2 },
    { timestamp: "14:06", redis_utilization: 100, checkout_504_pct: 91.8, ingress_rps: 1198, internal_retries: 14.9 },
    { timestamp: "14:12", redis_utilization: 100, checkout_504_pct: 93.1, ingress_rps: 1202, internal_retries: 15.8 },
    { timestamp: "14:18", redis_utilization: 100, checkout_504_pct: 92.0, ingress_rps: 1218, internal_retries: 15.1 },
    { timestamp: "14:24", redis_utilization: 45, checkout_504_pct: 22.3, ingress_rps: 1214, internal_retries: 4.2 },
    { timestamp: "14:25", redis_utilization: 14, checkout_504_pct: 0.02, ingress_rps: 1208, internal_retries: 1.0 },
    { timestamp: "14:30", redis_utilization: 13, checkout_504_pct: 0.01, ingress_rps: 1212, internal_retries: 1.0 },
  ],
};

export const MOCK_THREADS: Thread[] = [
  {
    thread_id: "thread-checkout-504-oct28",
    title: "Checkout API 504 Outage on Oct 28",
    created_at: "2026-10-28T14:30:00Z",
    updated_at: "2026-10-28T14:35:10Z",
    message_count: 2,
    status: "active",
    last_run_id: "run-checkout-001",
  },
  {
    thread_id: "thread-redis-slowdown",
    title: "Database slowdown vs DDoS analysis",
    created_at: "2026-10-27T09:15:00Z",
    updated_at: "2026-10-27T09:22:00Z",
    message_count: 4,
    status: "active",
    last_run_id: "run-redis-002",
  },
  {
    thread_id: "thread-payment-webhook",
    title: "Payment Gateway webhook dropped requests",
    created_at: "2026-10-25T16:40:00Z",
    updated_at: "2026-10-25T16:55:00Z",
    message_count: 2,
    status: "active",
    last_run_id: "run-payment-003",
  },
];

export const MOCK_MESSAGES_MAP: Record<string, ChatMessage[]> = {
  "thread-checkout-504-oct28": [
    {
      message_id: "msg-user-1",
      thread_id: "thread-checkout-504-oct28",
      role: "user",
      content:
        "Why did Checkout API fail on October 28 between 14:00 and 14:25 UTC, and do we owe Acme Corp an SLA penalty?",
      created_at: "2026-10-28T14:30:05Z",
      run_id: "run-checkout-001",
    },
    {
      message_id: "msg-assistant-1",
      thread_id: "thread-checkout-504-oct28",
      role: "assistant",
      content: `The Checkout API outage between 14:00 and 14:25 UTC was caused by **Redis connection pool exhaustion** following the deployment of PR #812 [EVD-001] to the **Auth Service** at 13:58 UTC.

### Investigation Findings
- **Root Cause**: PR #812 mistakenly reduced \`max_connections\` from 500 to 50 [EVD-001]. During normal peak traffic, the connection pool saturated at 100% within two minutes [EVD-002], causing session verification timeouts.
- **DDoS Hypothesis Refuted**: While team members raised concerns about an external volumetric DDoS in Slack [EVD-005], Cloudflare ingress telemetry remained completely steady at 1,210 RPS [EVD-004]. The spike was caused by unthrottled internal retries cascading from Checkout API (15x retry amplification).
- **Resolution**: An emergency rollback (PR #813 [EVD-003]) restored the pool size to 500 at 14:24 UTC, returning Checkout 504 errors to baseline (0.01%) immediately [EVD-002].
- **SLA Impact**: Total downtime was **23 minutes**. Under the Acme Corp Master Services Agreement, an RCA is mandatory within 5 business days, but **0% financial service credits** are owed (credits only apply past 60 minutes).

You can inspect the full root cause card, incident timeline, topology graph, and evidence citations in the inspector panel on the right.`,
      created_at: "2026-10-28T14:30:25Z",
      run_id: "run-checkout-001",
      metadata: {
        investigation_result: MOCK_INVESTIGATION_RESULT,
        citations: MOCK_INVESTIGATION_RESULT.supporting_evidence,
      },
    },
  ],
};

