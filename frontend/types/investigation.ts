/**
 * Investigation result and evidence domain types aligned with backend schemas.
 */

export type RootCauseStatus = "confirmed" | "likely" | "possible" | "unknown";

export type InvestigationStatus =
  | "completed"
  | "needs_clarification"
  | "insufficient_evidence"
  | "failed";

export type SLAStatus = "assessed" | "unable_to_determine" | "not_applicable";

export type EvidenceClassification =
  | "supporting"
  | "contradicting"
  | "contextual"
  | "unverified";

export interface Citation {
  file_name?: string | null;
  line_start?: number | null;
  line_end?: number | null;
  page?: number | null;
}

export interface EvidenceItem {
  evidence_id: string;
  source_type: string;
  source_id: string;
  title: string;
  content: string;
  service_id?: string | null;
  timestamp?: string | null;
  citation?: Citation | Record<string, unknown> | null;
  retrieval_method?: string;
  relevance_score?: number | null;
  classification?: EvidenceClassification | string;
  asset_file_id?: string | null; // For visual evidence like Grafana screenshots
}

export interface RootCause {
  title: string;
  explanation: string;
  status: RootCauseStatus;
  confidence?: string;
}

export interface AffectedService {
  service_id: string;
  impact: string;
  type?: "failing" | "upstream" | "downstream" | "normal" | "root_cause" | "impacted";
}

export interface TimelineEvent {
  timestamp: string;
  title: string;
  description: string;
  evidence_ids?: string[];
}

export interface SLAAssessment {
  status: SLAStatus;
  customer_id?: string | null;
  downtime_minutes?: number | null;
  rca_required: boolean;
  credit_percent: number;
  explanation: string;
}

export interface ServiceNode {
  id: string;
  label: string;
  status: "failing" | "impacted" | "healthy" | "root_cause";
  metrics?: Record<string, string | number>;
}

export interface ServiceEdge {
  from: string;
  to: string;
  label?: string;
}

export interface ServiceGraph {
  nodes: ServiceNode[];
  edges: ServiceEdge[];
}

export interface TelemetryPoint {
  timestamp: string;
  [metricName: string]: string | number;
}

export interface InvestigationResult {
  investigation_status: InvestigationStatus;
  incident_id?: string | null;
  summary: string;
  root_cause?: RootCause | null;
  affected_services: AffectedService[];
  timeline: TimelineEvent[];
  supporting_evidence: EvidenceItem[];
  contradicting_evidence: EvidenceItem[];
  sla_assessment?: SLAAssessment | null;
  recommendations: string[];
  missing_evidence: string[];
  citations: (EvidenceItem | Record<string, unknown>)[];
  service_graph?: ServiceGraph | null;
  telemetry_series?: TelemetryPoint[] | null;
}
