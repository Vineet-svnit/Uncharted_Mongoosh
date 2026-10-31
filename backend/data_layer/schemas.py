"""
backend/data_layer/schemas.py
------------------------------
Python TypedDicts / dataclasses that document the shape of every
MongoDB document.  Nothing is enforced at the DB level, but these
definitions make integration with Member 2 explicit.
"""

from __future__ import annotations

from typing import Any, TypedDict


# ── services ──────────────────────────────────────────────────────────────────

class ServiceDoc(TypedDict):
    service_id: str
    name: str
    service_type: str          # "api" | "service" | "database" | "cache"
    owner_team: str
    environment: str
    topology_version: str
    depends_on: list[str]      # list of service_ids
    criticality: str           # "critical" | "high" | "medium" | "low"
    description: str


# ── deployments ───────────────────────────────────────────────────────────────

class CitationDoc(TypedDict):
    file_name: str
    line_start: int | None
    line_end: int | None
    page: int | None


class DeploymentDoc(TypedDict):
    deployment_id: str
    pr_number: int
    commit_hash: str
    service_id: str
    deployed_at: str           # ISO-8601
    environment: str
    status: str                # "success" | "rolled_back" | "failed"
    files_changed: list[str]
    change_description: str
    code_diff: str
    previous_config: dict[str, Any]
    updated_config: dict[str, Any]
    deployed_by: str
    rollback_of: str | None    # deployment_id this rolls back, if applicable


# ── knowledge_chunks ──────────────────────────────────────────────────────────

class KnowledgeChunkDoc(TypedDict):
    document_id: str
    source_id: str
    source_type: str           # "pr_diff"|"runbook"|"postmortem"|"sla_text"|"incident_summary"
    source_file: str
    title: str
    content: str
    service_id: str | None
    incident_id: str | None
    customer_id: str | None
    environment: str | None
    timestamp: str | None      # ISO-8601
    citation: CitationDoc
    embedding: list[float] | None


# ── telemetry_events ──────────────────────────────────────────────────────────

class TelemetryDoc(TypedDict):
    event_id: str
    incident_id: str
    service_id: str
    environment: str
    timestamp: str             # ISO-8601
    record_type: str           # "metric" | "log" | "trace"
    event_type: str
    metric_name: str | None
    metric_value: float | None
    unit: str | None
    severity: str              # "ok" | "warning" | "critical"
    message: str
    trace_id: str | None
    source: str


# ── incident_messages ─────────────────────────────────────────────────────────

class MessageDoc(TypedDict):
    message_id: str
    incident_id: str
    channel: str
    sender: str
    sender_role: str
    timestamp: str             # ISO-8601
    text: str
    thread_id: str | None
    embedding: list[float] | None


# ── sla_clauses ───────────────────────────────────────────────────────────────

class SlaClauseDoc(TypedDict):
    clause_id: str
    contract_id: str
    customer_id: str
    customer_name: str
    contract_version: str
    clause_number: str
    page: int
    title: str
    content: str
    # Structured threshold fields (None for non-threshold clauses)
    downtime_min_minutes: int | None
    downtime_max_minutes: int | None   # None = no upper bound
    financial_credit_pct: float | None
    rca_required: bool | None
    is_active: bool


# ── visual_evidence ───────────────────────────────────────────────────────────

class VisualEvidenceDoc(TypedDict):
    evidence_id: str
    incident_id: str
    title: str
    description: str
    gridfs_file_id: str        # str(ObjectId)
    file_name: str
    mime_type: str
    captured_at: str           # ISO-8601
    embedding: list[float] | None


# ── incidents ─────────────────────────────────────────────────────────────────

class IncidentDoc(TypedDict):
    incident_id: str
    title: str
    environment: str
    affected_services: list[str]
    customer_id: str
    start_time: str            # ISO-8601
    end_time: str | None
    customer_impact_start: str | None
    customer_impact_end: str | None
    downtime_minutes: int | None
    status: str                # "open" | "resolved" | "postmortem"
    severity: str
    root_cause_summary: str | None
    resolved_at: str | None

