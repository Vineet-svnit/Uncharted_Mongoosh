from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class RootCauseStatus(str, Enum):
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    POSSIBLE = "possible"
    UNKNOWN = "unknown"


class InvestigationStatus(str, Enum):
    COMPLETED = "completed"
    NEEDS_CLARIFICATION = "needs_clarification"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    FAILED = "failed"


class SLAStatus(str, Enum):
    ASSESSED = "assessed"
    UNABLE_TO_DETERMINE = "unable_to_determine"
    NOT_APPLICABLE = "not_applicable"


class EvidenceClassification(str, Enum):
    SUPPORTING = "supporting"
    CONTRADICTING = "contradicting"
    CONTEXTUAL = "contextual"
    UNVERIFIED = "unverified"


class Citation(BaseModel):
    file_name: str
    line_start: int | None = None
    line_end: int | None = None
    page: int | None = None


class EvidenceItem(BaseModel):
    evidence_id: str
    source_type: str
    source_id: str
    title: str
    content: str
    service_id: str | None = None
    timestamp: str | None = None
    citation: Citation | dict[str, Any] | None = None
    retrieval_method: str = "direct"
    relevance_score: float | None = None
    classification: EvidenceClassification = EvidenceClassification.SUPPORTING


class RootCause(BaseModel):
    title: str
    explanation: str
    status: RootCauseStatus = RootCauseStatus.LIKELY
    confidence: str = "high"


class AffectedService(BaseModel):
    service_id: str
    impact: str


class TimelineItem(BaseModel):
    timestamp: str
    title: str
    description: str
    evidence_ids: list[str] = Field(default_factory=list)


class SLAAssessment(BaseModel):
    status: SLAStatus = SLAStatus.NOT_APPLICABLE
    customer_id: str | None = None
    downtime_minutes: int | None = None
    rca_required: bool = False
    credit_percent: float = 0.0
    explanation: str


class InvestigationReport(BaseModel):
    investigation_status: InvestigationStatus = InvestigationStatus.COMPLETED
    incident_id: str | None = None
    summary: str
    root_cause: RootCause | None = None
    affected_services: list[AffectedService] = Field(default_factory=list)
    timeline: list[TimelineItem] = Field(default_factory=list)
    supporting_evidence: list[EvidenceItem] = Field(default_factory=list)
    contradicting_evidence: list[EvidenceItem] = Field(default_factory=list)
    sla_assessment: SLAAssessment | None = None
    recommendations: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)

