import { InvestigationResult, EvidenceItem } from "./investigation";

export interface ChatMessageMetadata {
  investigation_result?: InvestigationResult;
  citations?: EvidenceItem[];
  run_id?: string;
  stage?: string;
  [key: string]: unknown;
}

export interface ChatMessage {
  message_id: string;
  thread_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
  run_id?: string | null;
  metadata?: ChatMessageMetadata;
}

export interface Thread {
  thread_id: string;
  title: string;
  created_at: string;
  updated_at?: string | null;
  message_count: number;
  status: "active" | "archived" | "deleted";
  last_run_id?: string | null;
}

export type ToolStatus = "pending" | "running" | "completed" | "failed";

export interface ToolExecution {
  id: string;
  tool: string;
  label: string;
  status: ToolStatus;
  started_at?: string;
  completed_at?: string;
  evidence_count?: number;
  message?: string;
  summary?: string;
}

export type InvestigationStage =
  | "idle"
  | "planning"
  | "investigating"
  | "verification"
  | "report_generation"
  | "completed"
  | "failed";

