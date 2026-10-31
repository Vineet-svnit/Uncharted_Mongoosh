import {
  HealthResponse,
  ThreadResponse,
  ThreadListResponse,
  ThreadMessagesResponse,
  StreamEventHandlers,
  DeleteThreadResponse,
} from "@/types/api";
import { Thread, ChatMessage } from "@/types/chat";
import { streamInvestigation } from "./sse";
import {
  MOCK_THREADS,
  MOCK_MESSAGES_MAP,
  MOCK_INVESTIGATION_RESULT,
} from "./mock-data";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const IS_MOCK_MODE =
  process.env.NEXT_PUBLIC_USE_MOCK_API === "true";

// In-memory store for mock mode only (completely isolated)
const mockThreadsState: Thread[] = [...MOCK_THREADS];
const mockMessagesState: Record<string, ChatMessage[]> = {
  ...MOCK_MESSAGES_MAP,
};

/**
 * Health check
 */
export async function getHealth(): Promise<HealthResponse> {
  if (IS_MOCK_MODE) {
    return {
      status: "ok",
      mongodb: "mock-connected",
      agent: "mock-initialized",
      data_layer: "mock-active",
    };
  }

  const res = await fetch(`${API_BASE_URL}/health`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Health check failed: HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Create a new conversation thread
 */
export async function createThread(title?: string): Promise<ThreadResponse> {
  if (IS_MOCK_MODE) {
    const threadId = `mock-thread-${Date.now()}`;
    const newThread: Thread = {
      thread_id: threadId,
      title: title || "New Investigation",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      message_count: 0,
      status: "active",
      last_run_id: null,
    };
    mockThreadsState.unshift(newThread);
    mockMessagesState[threadId] = [];
    return newThread;
  }

  const res = await fetch(`${API_BASE_URL}/api/chat/threads`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ title }),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(
      `Failed to create thread (${res.status}): ${errorText || res.statusText}`
    );
  }
  return res.json();
}

/**
 * List all conversation threads
 */
export async function getThreads(limit: number = 50): Promise<ThreadListResponse> {
  if (IS_MOCK_MODE) {
    return {
      threads: [...mockThreadsState],
    };
  }

  const res = await fetch(`${API_BASE_URL}/api/chat/threads?limit=${limit}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch threads: HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Get thread metadata
 */
export async function getThread(threadId: string): Promise<ThreadResponse> {
  if (IS_MOCK_MODE) {
    const found = mockThreadsState.find((t) => t.thread_id === threadId);
    if (!found) {
      throw new Error(`Mock thread ${threadId} not found`);
    }
    return found;
  }

  const res = await fetch(`${API_BASE_URL}/api/chat/threads/${threadId}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch thread ${threadId}: HTTP ${res.status}`);
  }
  return res.json();
}

/**
 * Get chronological chat history for a thread
 */
export async function getThreadMessages(
  threadId: string,
  limit: number = 100
): Promise<ThreadMessagesResponse> {
  if (IS_MOCK_MODE) {
    const msgs = mockMessagesState[threadId] || [];
    return {
      thread_id: threadId,
      messages: [...msgs],
    };
  }

  const res = await fetch(
    `${API_BASE_URL}/api/chat/threads/${threadId}/messages?limit=${limit}`,
    {
      cache: "no-store",
    }
  );

  if (!res.ok) {
    throw new Error(
      `Failed to fetch messages for thread ${threadId}: HTTP ${res.status}`
    );
  }
  return res.json();
}

/**
 * Delete a thread
 */
export async function deleteThread(
  threadId: string
): Promise<DeleteThreadResponse> {
  if (IS_MOCK_MODE) {
    const idx = mockThreadsState.findIndex((t) => t.thread_id === threadId);
    if (idx !== -1) {
      mockThreadsState.splice(idx, 1);
    }
    delete mockMessagesState[threadId];
    return {
      status: "success",
      message: `Thread '${threadId}' deleted (demo mode).`,
    };
  }

  const res = await fetch(`${API_BASE_URL}/api/chat/threads/${threadId}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    throw new Error(
      `Failed to delete thread ${threadId}: HTTP ${res.status}`
    );
  }
  return res.json();
}

/**
 * Stream an investigation query via SSE
 */
export async function streamMessage(
  threadId: string,
  message: string,
  handlers: StreamEventHandlers,
  signal?: AbortSignal
): Promise<void> {
  if (IS_MOCK_MODE) {
    await simulateMockStream(threadId, message, handlers, signal);
    return;
  }

  await streamInvestigation({
    url: API_BASE_URL,
    threadId,
    message,
    handlers,
    signal,
  });
}

/**
 * Construct URL for visual asset stored in GridFS
 */
export function getEvidenceAssetUrl(fileId: string): string {
  if (IS_MOCK_MODE) {
    // Return SVG data URI for demo mock mode
    return `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400" viewBox="0 0 800 400"><rect width="800" height="400" fill="%230f172a"/><text x="400" y="50" font-family="sans-serif" font-size="20" font-weight="bold" fill="%2338bdf8" text-anchor="middle">Grafana Dashboard: Redis Connection Saturation &amp; 504 Errors</text><polyline fill="none" stroke="%23fb7185" stroke-width="3" points="50,300 150,300 250,290 320,80 450,75 580,85 650,290 750,300"/><polyline fill="none" stroke="%23f59e0b" stroke-width="2" points="50,320 200,320 300,310 320,120 450,110 580,115 650,315 750,320"/><text x="60" y="90" font-family="sans-serif" font-size="12" fill="%23fb7185">Redis Pool Usage (100% Saturation)</text><text x="60" y="115" font-family="sans-serif" font-size="12" fill="%23f59e0b">Checkout 504 Error Rate (92.4%)</text><line x1="50" y1="330" x2="750" y2="330" stroke="%23334155" stroke-width="1"/><text x="50" y="355" font-family="sans-serif" font-size="11" fill="%2394a3b8">13:50 UTC</text><text x="320" y="355" font-family="sans-serif" font-size="11" fill="%23fb7185">14:01 (Outage Start)</text><text x="650" y="355" font-family="sans-serif" font-size="11" fill="%2334d399">14:24 (Rollback)</text></svg>`;
  }
  return `${API_BASE_URL.replace(/\/$/, "")}/api/evidence/assets/${fileId}`;
}

/**
 * High-fidelity Mock stream generator for independent UI development
 */
async function simulateMockStream(
  threadId: string,
  message: string,
  handlers: StreamEventHandlers,
  signal?: AbortSignal
): Promise<void> {
  const runId = `mock-run-${Date.now()}`;
  const delay = (ms: number) =>
    new Promise<void>((resolve, reject) => {
      const timer = setTimeout(resolve, ms);
      signal?.addEventListener("abort", () => {
        clearTimeout(timer);
        reject(new Error("Aborted"));
      });
    });

  try {
    // 1. run_started
    handlers.onRunStarted?.({ run_id: runId, thread_id: threadId });
    await delay(350);

    // 2. status: planning
    handlers.onStatus?.({
      stage: "planning",
      message: "Parsing incident query and extracting key entities...",
    });
    await delay(500);

    // 3. tool_started & completed: trace_service_dependencies
    handlers.onToolStarted?.({
      tool: "trace_service_dependencies",
      message: "Tracing service dependencies for checkout-api",
    });
    await delay(700);
    handlers.onToolCompleted?.({
      tool: "trace_service_dependencies",
      evidence_count: 3,
      summary: "Identified downstream: auth-service, redis-cluster-east",
    });
    await delay(350);

    // 4. tool_started & completed: find_recent_deployments
    handlers.onToolStarted?.({
      tool: "find_recent_deployments",
      message: "Searching recent deployments across auth-service",
    });
    await delay(800);
    handlers.onToolCompleted?.({
      tool: "find_recent_deployments",
      evidence_count: 2,
      summary: "Found PR #812 deployed 13:58 UTC (reduced pool size to 50)",
    });
    await delay(400);

    // 5. tool_started & completed: query_service_telemetry
    handlers.onToolStarted?.({
      tool: "query_service_telemetry",
      message: "Querying Redis connection saturation & 504 error telemetry",
    });
    await delay(750);
    handlers.onToolCompleted?.({
      tool: "query_service_telemetry",
      evidence_count: 4,
      summary: "Redis pool hit 100% saturation at 14:01 UTC; 504 errors spiked to 92.4%",
    });
    await delay(350);

    // 6. tool_started & completed: search_incident_messages
    handlers.onToolStarted?.({
      tool: "search_incident_messages",
      message: "Reviewing Slack war room channel #incident-checkout",
    });
    await delay(650);
    handlers.onToolCompleted?.({
      tool: "search_incident_messages",
      evidence_count: 2,
      summary: "War room raised DDoS hypothesis; refuted by Cloudflare ingress data",
    });
    await delay(350);

    // 7. tool_started & completed: retrieve_customer_sla
    handlers.onToolStarted?.({
      tool: "retrieve_customer_sla",
      message: "Reviewing Acme Corp SLA terms & downtime penalties",
    });
    await delay(500);
    handlers.onToolCompleted?.({
      tool: "retrieve_customer_sla",
      evidence_count: 1,
      summary: "23m downtime requires RCA report, 0% financial credit",
    });
    await delay(400);

    // 8. status: verification
    handlers.onStatus?.({
      stage: "verification",
      message: "Cross-checking supporting and contradictory evidence...",
    });
    await delay(600);

    // 9. assistant_result
    const msgId = `mock-msg-${Date.now()}`;
    const assistantContent = `Based on the investigation, the root cause of the Checkout API 504 errors on October 28 was **Redis connection pool exhaustion** caused by the deployment of PR #812 [EVD-001] to Auth Service at 13:58 UTC.

### Key Highlights
- **Configuration Regression**: PR #812 reduced the maximum Redis connection pool from 500 to 50 [EVD-001]. At 14:01 UTC, regular production traffic saturated all 50 connections [EVD-002].
- **Contradiction Resolved**: Initial Slack discussions suspected a volumetric DDoS attack [EVD-005]. Ingress traffic metrics showed flat traffic at 1,210 RPS, disproving an external attack [EVD-004]. The load surge was internal retries escalating 15x.
- **Remediation**: Reverting the pool size to 500 via emergency PR #813 [EVD-003] resolved the issue at 14:24 UTC.
- **SLA Assessment**: 23 minutes downtime for Acme Corp triggers an RCA delivery requirement within 5 business days, with **0% financial penalty credit** due.

Review the complete root cause assessment, topology graph, timeline, and evidence citations in the inspector to the right.`;

    const assistantResult = {
      message_id: msgId,
      content: assistantContent,
      investigation_result: MOCK_INVESTIGATION_RESULT,
    };
    handlers.onAssistantResult?.(assistantResult);

    // Save in mock messages memory
    if (!mockMessagesState[threadId]) {
      mockMessagesState[threadId] = [];
    }
    // Add user message if not already added
    const userMsg: ChatMessage = {
      message_id: `mock-user-${Date.now()}`,
      thread_id: threadId,
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
      run_id: runId,
    };
    const asstMsg: ChatMessage = {
      message_id: msgId,
      thread_id: threadId,
      role: "assistant",
      content: assistantContent,
      created_at: new Date().toISOString(),
      run_id: runId,
      metadata: {
        investigation_result: MOCK_INVESTIGATION_RESULT,
        citations: MOCK_INVESTIGATION_RESULT.supporting_evidence,
      },
    };
    mockMessagesState[threadId].push(userMsg, asstMsg);

    // Update mock thread
    const targetThread = mockThreadsState.find((t) => t.thread_id === threadId);
    if (targetThread) {
      targetThread.message_count += 2;
      targetThread.updated_at = new Date().toISOString();
      targetThread.last_run_id = runId;
    }

    await delay(300);

    // 10. done
    handlers.onDone?.({ run_id: runId, thread_id: threadId });
  } catch (err: unknown) {
    if (signal?.aborted) return;
    handlers.onError?.({
      code: "MOCK_STREAM_ERROR",
      message: err instanceof Error ? err.message : "Mock stream error",
    });
  }
}

