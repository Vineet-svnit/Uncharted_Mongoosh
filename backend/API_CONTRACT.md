# AegisRCA Backend Integration Contract (for Frontend / Member 3)

This document specifies the exact API contract provided by the AegisRCA Agentic AI Engine & FastAPI backend for the Next.js 14 frontend.

---

## 1. API Base URL

- **Development Base URL**: `http://localhost:8000`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`
- **Allowed Frontend Origin (CORS)**: `http://localhost:3000` (configurable via `FRONTEND_ORIGIN`)

---

## 2. Complete Endpoint Summary

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend and service health check |
| `POST` | `/api/chat/threads` | Create a new conversation thread |
| `GET` | `/api/chat/threads` | List all conversation threads (most recent first) |
| `GET` | `/api/chat/threads/{thread_id}` | Retrieve thread metadata |
| `GET` | `/api/chat/threads/{thread_id}/messages` | Get full chronological message history for a thread |
| `POST` | `/api/chat/threads/{thread_id}/messages/stream` | Send message and receive SSE investigation stream |
| `DELETE` | `/api/chat/threads/{thread_id}` | Delete conversation thread, runs, reports, and memory |
| `GET` | `/api/evidence/assets/{file_id}` | Retrieve raw screenshot image bytes (e.g. Grafana dashboards) |

---

## 3. Endpoints and Schemas

### 3.1 Health Check

```http
GET /health
```

**Response (`200 OK`):**

```json
{
  "status": "ok",
  "mongodb": "connected",
  "agent": "initialized",
  "data_layer": "connected"
}
```

---

### 3.2 Create Conversation Thread

```http
POST /api/chat/threads
Content-Type: application/json
```

**Request Body (Optional):**

```json
{
  "title": "Checkout API 504 Outage Investigation"
}
```

**Response (`201 Created`):**

```json
{
  "thread_id": "7b8d8cf9-1910-4bf6-9ea6-8c4d2925b42c",
  "title": "Checkout API 504 Outage Investigation",
  "created_at": "2026-10-28T14:30:00Z",
  "updated_at": "2026-10-28T14:30:00Z",
  "message_count": 0,
  "status": "active",
  "last_run_id": null
}
```

---

### 3.3 List Conversation Threads

```http
GET /api/chat/threads?limit=50
```

**Response (`200 OK`):**

```json
{
  "threads": [
    {
      "thread_id": "7b8d8cf9-1910-4bf6-9ea6-8c4d2925b42c",
      "title": "Checkout API 504 Outage Investigation",
      "created_at": "2026-10-28T14:30:00Z",
      "updated_at": "2026-10-28T14:32:15Z",
      "message_count": 2,
      "status": "active",
      "last_run_id": "d13f9c65-68fe-4e3a-86c4-6c39f2da504d"
    }
  ]
}
```

---

### 3.4 Get Thread Messages History

```http
GET /api/chat/threads/{thread_id}/messages
```

**Response (`200 OK`):**

```json
{
  "thread_id": "7b8d8cf9-1910-4bf6-9ea6-8c4d2925b42c",
  "messages": [
    {
      "message_id": "9a01bf28-765e-4b6e-a745-9252c7908b90",
      "thread_id": "7b8d8cf9-1910-4bf6-9ea6-8c4d2925b42c",
      "role": "user",
      "content": "Why did Checkout API throw 504 errors on October 28 between 14:00 and 14:25 UTC, and do we owe Acme Corp an SLA penalty?",
      "created_at": "2026-10-28T14:30:05Z",
      "run_id": "d13f9c65-68fe-4e3a-86c4-6c39f2da504d",
      "metadata": {}
    },
    {
      "message_id": "4e72aa19-58cb-46b0-9b8e-324f2e96031b",
      "thread_id": "7b8d8cf9-1910-4bf6-9ea6-8c4d2925b42c",
      "role": "assistant",
      "content": "Checkout API experienced high rates of 504 Gateway Timeouts between 14:00 and 14:25 UTC due to Redis connection pool exhaustion following PR #812.",
      "created_at": "2026-10-28T14:30:18Z",
      "run_id": "d13f9c65-68fe-4e3a-86c4-6c39f2da504d",
      "metadata": {
        "investigation_result": {
          "investigation_status": "completed",
          "incident_id": "INC-2026-10-28-001",
          "summary": "...",
          "root_cause": { ... }
        }
      }
    }
  ]
}
```

---

### 3.5 Send Message and Stream Investigation (SSE)

```http
POST /api/chat/threads/{thread_id}/messages/stream
Content-Type: application/json
Accept: text/event-stream
```

**Request Body:**

```json
{
  "message": "Why did Checkout API throw 504 errors on October 28 between 14:00 and 14:25 UTC, and do we owe Acme Corp an SLA penalty?"
}
```

**Response Format**: Server-Sent Events (`text/event-stream`).

#### Event Stream Sequence:

1. `event: run_started`
   ```json
   {"run_id": "d13f9c65-68fe-4e3a-86c4-6c39f2da504d", "thread_id": "7b8d8cf9-1910-4bf6-9ea6-8c4d2925b42c"}
   ```

2. `event: status`
   ```json
   {"stage": "planning", "message": "Understanding the incident query"}
   ```

3. `event: tool_started`
   ```json
   {"tool": "trace_service_dependencies", "message": "Running investigation tool: trace_service_dependencies"}
   ```

4. `event: tool_completed`
   ```json
   {"tool": "investigation_tools", "evidence_count": 4}
   ```

5. `event: status`
   ```json
   {"stage": "verification", "message": "Cross-checking supporting and contradictory evidence"}
   ```

6. `event: assistant_result`
   ```json
   {
     "message_id": "4e72aa19-58cb-46b0-9b8e-324f2e96031b",
     "content": "Checkout API experienced high rates of 504 Gateway Timeouts...",
     "investigation_result": {
       "investigation_status": "completed",
       "incident_id": "INC-2026-10-28-001",
       "summary": "Checkout API experienced 504 errors due to Redis pool exhaustion following PR #812.",
       "root_cause": {
         "title": "Redis connection pool configuration regression",
         "explanation": "PR #812 reduced Redis max_connections from 500 to 50 in Auth Service...",
         "status": "likely",
         "confidence": "high"
       },
       "affected_services": [
         {"service_id": "checkout-api", "impact": "504 Gateway Timeout responses spiking to 92%"},
         {"service_id": "auth-service", "impact": "Authentication request timeouts and 15x retries"},
         {"service_id": "redis-cluster-east", "impact": "Connection pool saturation at 100% (50/50 connections)"}
       ],
       "timeline": [
         {
           "timestamp": "2026-10-28T13:58:00Z",
           "title": "PR #812 deployed to Auth Service",
           "description": "Configuration change reduced Redis connection pool size from 500 to 50.",
           "evidence_ids": ["EVD-001"]
         },
         {
           "timestamp": "2026-10-28T14:01:00Z",
           "title": "Redis Pool Saturation & 504 Spikes",
           "description": "Redis pool reached 100% capacity; Checkout API 504 Gateway Timeouts surged to 92%.",
           "evidence_ids": ["EVD-002"]
         },
         {
           "timestamp": "2026-10-28T14:24:00Z",
           "title": "Rollback of PR #812 & Recovery",
           "description": "Rollback restored healthy pool capacity and 504 errors dropped to normal baseline.",
           "evidence_ids": ["EVD-003"]
         }
       ],
       "supporting_evidence": [
         {
           "evidence_id": "EVD-001",
           "source_type": "deployment_pr",
           "source_id": "PR-812",
           "title": "Fix Redis connection pool config leak and adjust default sizing",
           "content": "Deployment DEP-812 (PR PR-812): Reduced connection pool from 500 to 50...",
           "service_id": "auth-service",
           "timestamp": "2026-10-28T13:58:00Z",
           "citation": {
             "file_name": "GitHub_PR_812.json",
             "line_start": 44,
             "line_end": 48,
             "page": null
           },
           "retrieval_method": "direct_query",
           "relevance_score": 1.0,
           "classification": "supporting"
         }
       ],
       "contradicting_evidence": [
         {
           "evidence_id": "EVD-004",
           "source_type": "telemetry",
           "source_id": "METRIC-CHK-002",
           "title": "Telemetry observation: checkout-api",
           "content": "Telemetry snapshot for checkout-api at 2026-10-28T14:02:00Z: ingress_rps: 1210 (normal baseline)",
           "classification": "contradicting"
         }
       ],
       "sla_assessment": {
         "status": "assessed",
         "customer_id": "acme-corp",
         "downtime_minutes": 23,
         "rca_required": true,
         "credit_percent": 0.0,
         "explanation": "Under the Master Services Agreement for Acme Corp, downtime of 23 minutes requires a formal RCA report within 5 business days, with 0% financial penalty credit."
       },
       "recommendations": [
         "Restore and enforce minimum Redis connection pool size of 500 for auth-service in production.",
         "Implement connection pool utilization alerting at 80% threshold.",
         "Add circuit breaking and exponential backoff retry policies with jitter to avoid retry storms."
       ],
       "missing_evidence": [],
       "citations": [
         {
           "evidence_id": "EVD-001",
           "source_type": "deployment_pr",
           "source_id": "PR-812",
           "title": "Fix Redis connection pool config leak and adjust default sizing",
           "citation": {"file_name": "GitHub_PR_812.json", "line_start": 44, "line_end": 48}
         }
       ]
     }
   }
   ```

7. `event: done`
   ```json
   {"run_id": "d13f9c65-68fe-4e3a-86c4-6c39f2da504d", "thread_id": "7b8d8cf9-1910-4bf6-9ea6-8c4d2925b42c"}
   ```

8. `event: error` (Emitted only upon failure)
   ```json
   {
     "code": "INVESTIGATION_FAILED",
     "message": "Unable to complete the investigation: Database connection timeout"
   }
   ```

---

### 3.6 Frontend Fetch Streaming Example (Next.js / TypeScript)

```typescript
async function streamInvestigation(threadId: string, userMessage: string, onEvent: (eventType: string, data: any) => void) {
  const response = await fetch(`http://localhost:8000/api/chat/threads/${threadId}/messages/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message: userMessage }),
  });

  const reader = response.body?.getReader();
  if (!reader) throw new Error("ReadableStream not supported by response");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() || "";

    for (const chunk of lines) {
      if (!chunk.trim()) continue;
      const eventMatch = chunk.match(/^event:\s*(\w+)/m);
      const dataMatch = chunk.match(/^data:\s*(.+)$/m);

      if (eventMatch && dataMatch) {
        const eventType = eventMatch[1];
        const eventData = JSON.parse(dataMatch[1]);
        onEvent(eventType, eventData);
      }
    }
  }
}
```

---

### 3.7 Visual Evidence Asset Retrieval

```http
GET /api/evidence/assets/{file_id}
```

- Example: `GET /api/evidence/assets/gridfs_redis_001`
- **Response**: Binary image bytes with header `Content-Type: image/png`.
- In Next.js: `<img src="http://localhost:8000/api/evidence/assets/gridfs_redis_001" alt="Grafana Screenshot" />`

---

### 3.8 Delete Conversation Thread

```http
DELETE /api/chat/threads/{thread_id}
```

**Response (`200 OK`):**

```json
{
  "status": "success",
  "message": "Thread '7b8d8cf9-1910-4bf6-9ea6-8c4d2925b42c' and all associated records deleted."
}
```

