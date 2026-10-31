import { ChatMessage, Thread } from "./chat";
import { InvestigationResult } from "./investigation";

export interface HealthResponse {
  status: string;
  mongodb: string;
  agent: string;
  data_layer: string;
}

export interface ThreadCreateRequest {
  title?: string;
}

export interface ThreadResponse extends Thread {}

export interface ThreadListResponse {
  threads: Thread[];
}

export interface ThreadMessagesResponse {
  thread_id: string;
  messages: ChatMessage[];
}

export interface SendMessageRequest {
  message: string;
}

export interface DeleteThreadResponse {
  status: string;
  message: string;
}

// SSE Event payload schemas
export interface RunStartedPayload {
  run_id: string;
  thread_id: string;
}

export interface StatusPayload {
  stage: string;
  message: string;
}

export interface ToolStartedPayload {
  tool: string;
  message: string;
}

export interface ToolCompletedPayload {
  tool: string;
  evidence_count: number;
  summary?: string;
}

export interface AssistantResultPayload {
  message_id: string;
  content: string;
  investigation_result: InvestigationResult;
}

export interface DonePayload {
  run_id: string;
  thread_id: string;
}

export interface ErrorPayload {
  code?: string;
  message: string;
}

export type SSEEventMap = {
  run_started: RunStartedPayload;
  status: StatusPayload;
  tool_started: ToolStartedPayload;
  tool_completed: ToolCompletedPayload;
  assistant_result: AssistantResultPayload;
  done: DonePayload;
  error: ErrorPayload;
};

export interface StreamEventHandlers {
  onRunStarted?: (data: RunStartedPayload) => void;
  onStatus?: (data: StatusPayload) => void;
  onToolStarted?: (data: ToolStartedPayload) => void;
  onToolCompleted?: (data: ToolCompletedPayload) => void;
  onAssistantResult?: (data: AssistantResultPayload) => void;
  onDone?: (data: DonePayload) => void;
  onError?: (data: ErrorPayload) => void;
}

