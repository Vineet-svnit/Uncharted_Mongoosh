import {
  StreamEventHandlers,
  RunStartedPayload,
  StatusPayload,
  ToolStartedPayload,
  ToolCompletedPayload,
  AssistantResultPayload,
  DonePayload,
  ErrorPayload,
} from "@/types/api";

export interface StreamInvestigationOptions {
  url: string;
  threadId: string;
  message: string;
  handlers: StreamEventHandlers;
  signal?: AbortSignal;
}

/**
 * Parses and processes Server-Sent Events (SSE) from a POST ReadableStream.
 * Handles split chunks, multiple events per chunk, buffer preservation,
 * and JSON payload parsing.
 */
export async function streamInvestigation({
  url,
  threadId,
  message,
  handlers,
  signal,
}: StreamInvestigationOptions): Promise<void> {
  const fullUrl = `${url.replace(/\/$/, "")}/api/chat/threads/${threadId}/messages/stream`;

  let response: Response;
  try {
    response = await fetch(fullUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify({ message }),
      signal,
    });
  } catch (err: unknown) {
    if (signal?.aborted) {
      return; // Canceled intentionally
    }
    const errMsg = err instanceof Error ? err.message : "Failed to connect to backend stream";
    handlers.onError?.({
      code: "NETWORK_ERROR",
      message: `Connection failed: ${errMsg}. Ensure AegisRCA backend is running at ${url}`,
    });
    return;
  }

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Body was not json
    }
    handlers.onError?.({
      code: `HTTP_${response.status}`,
      message: errorDetail,
    });
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    handlers.onError?.({
      code: "NO_STREAM_BODY",
      message: "Server response does not support ReadableStream.",
    });
    return;
  }

  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      if (signal?.aborted) {
        await reader.cancel();
        break;
      }

      const { done, value } = await reader.read();
      if (done) {
        // Stream completed by remote server.
        // Flush remaining buffer if it contains any dangling event
        if (buffer.trim()) {
          parseAndDispatchSSEBlock(buffer, handlers);
        }
        break;
      }

      // Decode incoming chunk into stream buffer
      buffer += decoder.decode(value, { stream: true });

      // SSE blocks are separated by double newline (\n\n or \r\n\r\n)
      const blocks = buffer.split(/\r?\n\r?\n/);
      // The last element is either empty (if ended on boundary) or a partial event chunk
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        if (!block.trim()) continue;
        parseAndDispatchSSEBlock(block, handlers);
      }
    }
  } catch (err: unknown) {
    if (signal?.aborted) return;
    const errMsg = err instanceof Error ? err.message : "Stream reading interrupted";
    handlers.onError?.({
      code: "STREAM_READ_ERROR",
      message: errMsg,
    });
  } finally {
    reader.releaseLock();
  }
}

/**
 * Parses an individual SSE block consisting of `event:` and `data:` lines.
 */
function parseAndDispatchSSEBlock(block: string, handlers: StreamEventHandlers): void {
  const lines = block.split(/\r?\n/);
  let eventType = "message";
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trim());
    } else if (line.startsWith(":")) {
      // SSE comment / heartbeat - ignore safely
    }
  }

  if (dataLines.length === 0) return;

  const rawData = dataLines.join("\n");
  let parsedData: any;
  try {
    parsedData = JSON.parse(rawData);
  } catch {
    parsedData = rawData;
  }

  switch (eventType) {
    case "run_started":
      handlers.onRunStarted?.(parsedData as RunStartedPayload);
      break;
    case "status":
      handlers.onStatus?.(parsedData as StatusPayload);
      break;
    case "tool_started":
      handlers.onToolStarted?.(parsedData as ToolStartedPayload);
      break;
    case "tool_completed":
      handlers.onToolCompleted?.(parsedData as ToolCompletedPayload);
      break;
    case "assistant_result":
      handlers.onAssistantResult?.(parsedData as AssistantResultPayload);
      break;
    case "done":
      handlers.onDone?.(parsedData as DonePayload);
      break;
    case "error":
      handlers.onError?.(parsedData as ErrorPayload);
      break;
    default:
      // Unknown or custom event
      break;
  }
}

