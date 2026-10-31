# AegisRCA — AI-Powered SRE Incident Root Cause Analysis

> **AegisRCA** is an agentic AI system built for Site Reliability Engineers. It autonomously investigates production incidents, correlates evidence from multiple data sources, generates grounded Root Cause Analysis reports, and assesses SLA obligations — all in a real-time, evidence-traceable interface.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Proposed Solution](#2-proposed-solution)
3. [Example Investigation Scenarios](#3-example-investigation-scenarios)
4. [System Architecture](#4-system-architecture)
5. [Agentic Workflow](#5-agentic-workflow)
6. [Data Layer & MongoDB Design](#6-data-layer--mongodb-design)
7. [Search & Retrieval Architecture](#7-search--retrieval-architecture)
8. [Real-Time Streaming & Frontend](#8-real-time-streaming--frontend)
9. [Tech Stack](#9-tech-stack)
10. [Data Ingestion: Demo vs Production](#10-data-ingestion-demo-vs-production)
11. [Project Structure](#11-project-structure)
12. [Setup & Running](#12-setup--running)
13. [MongoDB Collections & Indexes](#13-mongodb-collections--indexes)
14. [Environment Configuration](#14-environment-configuration)

---

## 1. Problem Statement

When a production incident fires at 2 AM, an on-call SRE faces a high-pressure multi-source problem:

| Challenge | Reality |
|---|---|
| **Scattered evidence** | Deployment logs, Grafana dashboards, Slack war-room threads, telemetry metrics, runbooks, and SLA contracts all live in different systems |
| **Manual correlation** | Engineers spend 60–90% of incident time *finding* data, not *analyzing* it |
| **Time pressure** | Every minute of ambiguity translates to extended downtime and SLA breach risk |
| **SLA liability** | Contract clauses are buried in PDF documents; calculating breach thresholds and required penalties is manual and error-prone |
| **Knowledge silos** | Prior postmortems and runbooks that could have resolved the incident faster sit in wikis that no one remembers to check under pressure |
| **Unverifiable AI output** | Existing LLM chatbots hallucinate citations or make up metrics — dangerously misleading for SREs making real rollback/escalation decisions |

**The core pain**: There is no system that *automatically* pulls all relevant signals, correlates them against each other, verifies the evidence is real, and produces a structured, citation-backed RCA within minutes of the incident.

---

## 2. Proposed Solution

AegisRCA addresses this with a **multi-agent, evidence-grounded investigation system** built on four principles:

### 2.1 Principle 1: Agentic, Not Just Q&A
Instead of answering questions from memory, AegisRCA dispatches multiple specialized retrieval tools in parallel — just like a senior SRE would work through a checklist — and synthesizes only what it actually finds.

### 2.2 Principle 2: Every Claim is Grounded
All facts in the RCA output are traced to specific evidence items with source, timestamp, and citation (file name, line number, PDF page/clause). The system never invents evidence.

### 2.3 Principle 3: Dual-Layer Evidence Verification
Each evidence item carries two independent verification dimensions:
- **Source Verification** — *"Did this document/record actually exist in the database?"*
- **Claim Support** — *"Does this evidence support, contradict, or only partially address the hypothesis?"*

This prevents both hallucination (source doesn't exist) and misuse (source exists but doesn't support the claim).

### 2.4 Principle 4: Real-Time Transparency
The SRE watches every tool execute in real time via a streaming activity panel, can inspect evidence immediately on tool completion, and sees exactly which documents back each conclusion — before the full report is even generated.

---

## 3. Example Investigation Scenarios

The system is designed around four representative SRE queries, each exercising different investigative paths:

### Q1 — Primary Incident Investigation
> *"Why did Checkout API fail between 14:00 and 14:25 UTC on 2026-10-28, and do we owe Acme Corp an SLA penalty?"*

**What the agent does:**
1. Plans a full investigation: topology, deployments, telemetry, Slack, SLA
2. Calls 5 tools concurrently: `trace_service_dependencies`, `find_recent_deployments`, `query_service_telemetry`, `search_incident_messages`, `retrieve_customer_sla`
3. Discovers PR #812 reduced Redis `max_connections` from 500 → 50 in auth-service
4. Correlates telemetry spike (504 errors 92% at 14:01) with deployment timestamp (13:58)
5. Finds Slack contradiction: DDoS rumor ruled out by actual ingress telemetry (1210 req/s, normal baseline)
6. Calculates SLA: 23 min downtime → no financial credit, but formal RCA delivery within 5 business days required per clause 4.2

**Output:** COMPLETE RCA with timeline, dependency graph, supporting + contradicting evidence, SLA assessment

---

### Q2 — Historical Follow-Up / Pattern Query
> *"Have we experienced similar Redis connection pool exhaustion incidents before in auth-service?"*

**What the agent does:**
1. Recognizes intent as `historical_rag` / `follow_up_question`
2. Searches engineering knowledge base: runbooks, postmortems, prior incident summaries via hybrid vector+BM25 search
3. Retrieves matching postmortem documents if any exist
4. Falls back gracefully if no prior evidence — reports `INSUFFICIENT_EVIDENCE` with transparent missing-data explanation rather than fabricating

---

### Q3 — SLA Deep Dive
> *"What are our SLA obligations to Acme Corp for P1 incidents with > 20 minutes of downtime?"*

**What the agent does:**
1. Retrieves SLA contract clauses directly from MongoDB (structured — no embedding needed)
2. Runs deterministic SLA calculator against clause thresholds
3. Returns specific clause references with page/section numbers from the actual contract PDF

---

### Q4 — Cross-Incident Contradiction Analysis
> *"Was the Checkout API outage caused by a DDoS attack as some engineers suggested in Slack?"*

**What the agent does:**
1. Retrieves Slack war-room messages mentioning DDoS hypothesis
2. Cross-checks against actual telemetry: external ingress RPS at 14:00–14:25 UTC
3. DDoS hypothesis classified as `contradicting` evidence
4. Report clearly separates: *Supporting* (Redis pool exhaustion) vs *Contradicting* (DDoS claim disproved by telemetry)

---

## 4. System Architecture

```mermaid
flowchart TD
    subgraph FE["Frontend — Next.js 14"]
        UI["Chat Interface"]
        ACTIVITY["Investigation Activity Panel\n(Real-time tool stream)"]
        INSPECTOR["Investigation Inspector\n(Timeline · Topology · Evidence · SLA)"]
    end

    subgraph BE["Backend — FastAPI"]
        API["REST + SSE API\n/api/chat/stream"]
        SVC["InvestigationService\n(SSE event orchestrator)"]
        GRAPH["LangGraph Agent Graph"]
    end

    subgraph AGENT["LangGraph Agentic Workflow"]
        PLANNER["Planner Node\n(Intent classification)"]
        AGENT_NODE["Agent Node\n(LLM + Tool Calling)"]
        TOOLS_NODE["Tools Node\n(execute_tools)"]
        VERIFIER["Verifier Node\n(Evidence sufficiency)"]
        REPORT["Report Generator Node\n(Structured RCA)"]
    end

    subgraph DL["Data Layer"]
        ADAPTER["DataLayerAdapter\n(Normalizes to EvidenceItem)"]
        RETRIEVAL["retrieval.py\n(9 retrieval functions)"]
    end

    subgraph DB["MongoDB Atlas Local"]
        COL_SVC["services\n(topology graph)"]
        COL_DEP["deployments\n(CI/CD records)"]
        COL_TEL["telemetry_events\n(metrics + logs)"]
        COL_KB["knowledge_chunks\n(runbooks · postmortems · PRs)"]
        COL_MSG["incident_messages\n(Slack export)"]
        COL_SLA["sla_clauses\n(contract terms)"]
        COL_VIS["visual_evidence\n(Grafana screenshots)"]
        GRIDFS["GridFS\n(PDF + image binary)"]
    end

    subgraph LLM["AI Providers"]
        GEMINI["Google Gemini 2.5 Flash"]
        OPENAI["OpenAI GPT-4.1 Mini\n(USE_OPENAI=true)"]
        VOYAGE["Voyage AI multimodal-3.5\n(Embeddings + Reranker)"]
    end

    UI -->|"User query"| API
    API --> SVC
    SVC --> GRAPH
    GRAPH --> PLANNER --> AGENT_NODE
    AGENT_NODE -->|"tool_calls"| TOOLS_NODE
    TOOLS_NODE --> ADAPTER --> RETRIEVAL --> DB
    TOOLS_NODE -->|"evidence_items"| AGENT_NODE
    AGENT_NODE --> VERIFIER
    VERIFIER -->|"sufficient"| REPORT
    VERIFIER -->|"retry"| AGENT_NODE
    REPORT -->|"investigation_result"| SVC

    SVC -->|"SSE events"| API -->|"EventStream"| FE
    FE --> ACTIVITY
    FE --> INSPECTOR

    AGENT_NODE <--> LLM
    REPORT <--> LLM
    RETRIEVAL <--> VOYAGE
```

---

## 5. Agentic Workflow

The investigation is orchestrated by a **LangGraph StateGraph** with five nodes connected by conditional routing logic.

### 5.1 State Machine

```mermaid
stateDiagram-v2
    [*] --> planner

    planner --> agent : Normal query
    planner --> report_generator : Needs clarification

    agent --> tools : Has tool_calls AND iterations less than max
    agent --> verifier : No tool_calls OR max iterations reached

    tools --> agent : Returns evidence_items + ToolMessages

    verifier --> agent : Evidence insufficient AND retries remaining
    verifier --> report_generator : Evidence sufficient OR max retries reached

    report_generator --> [*]
```

### 5.2 Node Responsibilities

#### Planner Node — `plan_investigation`
- Receives the user's natural language query
- Classifies **intent**: `incident_investigation` | `follow_up_question` | `historical_rag` | `clarification_needed`
- Extracts: `service_id`, `incident_id`, `customer_id`, `time_range`, `required_sources`
- Sets `needs_clarification=True` if query is too ambiguous
- Uses LLM with structured output; falls back to heuristic regex-based planner

#### Agent Node — `agent_node`
- Core reasoning loop: LLM bound to 9 investigation tools
- On **iteration 0**: hard directive forces ≥2 tool calls (never skip evidence gathering)
- On **subsequent iterations**: uses verification feedback to target missing evidence
- Fallback: if LLM offline, deterministic tool selection based on plan intent

**Tool Selection by Intent (iteration 0):**

| Intent | Tools Dispatched |
|---|---|
| `incident_investigation` | `trace_service_dependencies`, `find_recent_deployments`, `query_service_telemetry`, `search_engineering_knowledge`, `search_incident_messages`, `retrieve_customer_sla` |
| `historical_rag` | `search_engineering_knowledge` ×2, `search_incident_messages`, `list_known_incidents`, `query_service_telemetry`, `find_recent_deployments` |

#### Tools Node — `execute_tools`
- Executes all tool calls from the agent in sequence
- Normalizes every tool output into structured `EvidenceItem` objects
- Handles 6 distinct output shapes: list payloads (deployments, knowledge, telemetry, messages, visual), topology dict, incident dict, SLA assessment dict
- Appends evidence items to `state["evidence_items"]` (accumulates across iterations)
- Writes audit log to `investigation_runs` collection

#### Verifier Node — `verify_evidence`
- LLM evaluates evidence sufficiency across 7 dimensions
- Conservative heuristic: only blocks as insufficient if *zero* evidence collected
- Returns `verification_feedback` string that guides next agent iteration
- Max retries: `MAX_VERIFICATION_ATTEMPTS` (default: 1)

#### Report Generator Node — `generate_report`
- Constructs final `InvestigationReport` with structured output schema
- Classifies evidence: `supporting` vs `contradicting` vs `contextual`
- Guarantees all `evidence_items` appear in the report (merge logic)
- Validates citations against real evidence IDs — no hallucinated references
- Computes `citation_coverage` percentage

### 5.3 Agent State Schema

```python
class AgentState(MessagesState):
    run_id:                 str           # Unique run identifier
    thread_id:              str           # Conversation thread
    investigation_plan:     dict          # Planner output (intent, ids, sources)
    evidence_items:         list[dict]    # Accumulated across tool iterations
    verification_feedback:  str | None    # Verifier guidance for retry
    verification_attempts:  int           # Retry counter
    tool_iterations:        int           # Tool execution rounds
    investigation_result:   dict | None   # Final InvestigationReport
    investigation_status:   str           # completed | insufficient_evidence | ...
```

### 5.4 SSE Event Sequence

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant API as FastAPI SSE
    participant GRAPH as LangGraph

    FE->>API: POST /api/chat/{thread_id}/stream
    API-->>FE: event: run_started {run_id}
    API-->>FE: event: status {stage: planning}
    GRAPH->>GRAPH: planner node
    API-->>FE: event: status {stage: planning_complete, sources: [...]}
    GRAPH->>GRAPH: agent node selects tools
    API-->>FE: event: tool_started {tool: find_recent_deployments}
    API-->>FE: event: tool_started {tool: query_service_telemetry}
    API-->>FE: event: tool_started {tool: trace_service_dependencies}
    GRAPH->>GRAPH: tools node executes all tools
    API-->>FE: event: tool_completed {tool: ..., evidence_count: N}
    API-->>FE: event: tool_completed {tool: ..., evidence_count: N}
    API-->>FE: event: status {stage: verification}
    GRAPH->>GRAPH: verifier + report_generator
    API-->>FE: event: assistant_result {investigation_result: {...}}
    API-->>FE: event: done
```

---

## 6. Data Layer & MongoDB Design

### 6.1 Collections Overview

| Collection | Purpose | Search Method |
|---|---|---|
| `services` | Microservice topology with `depends_on` edges | `$graphLookup` traversal |
| `deployments` | CI/CD deployment records, code diffs, PR metadata | Time-range filter |
| `telemetry_events` | Metrics, logs, traces per service per timestamp | Time-range filter |
| `knowledge_chunks` | Runbooks, postmortems, PR diffs, SLA text, incident summaries | Hybrid vector + BM25 + reranker |
| `incident_messages` | Slack war-room exports per incident | Hybrid vector + BM25 |
| `sla_clauses` | Structured SLA contract clauses with numeric thresholds | Exact match filter |
| `visual_evidence` | Grafana screenshot metadata with multimodal embeddings | Vector search |
| `chat_messages` | Per-thread conversation history | Lookup by thread_id |
| `investigation_runs` | Audit trail: tool events, timing, result counts | Lookup by run_id |
| `langgraph_checkpoints` | LangGraph agent state snapshots (multi-turn memory) | LangGraph internal |

### 6.2 Database Interaction with Agent Workflow

```mermaid
flowchart LR
    subgraph Agent["LangGraph Tools Node"]
        TN["execute_tools()"]
    end

    subgraph Adapter["DataLayerAdapter"]
        A1["find_recent_deployments"]
        A2["search_engineering_knowledge"]
        A3["query_service_telemetry"]
        A4["search_incident_messages"]
        A5["trace_service_dependencies"]
        A6["retrieve_customer_sla"]
        A7["search_visual_evidence"]
        A8["get_incident_details"]
        A9["list_known_incidents"]
    end

    subgraph MongoDB
        C1[("deployments")]
        C2[("knowledge_chunks\n+ embeddings")]
        C3[("telemetry_events")]
        C4[("incident_messages\n+ embeddings")]
        C5[("services\ndepends_on graph")]
        C6[("sla_clauses")]
        C7[("visual_evidence\n+ embeddings")]
        C8[("incidents")]
        GFS[("GridFS\nPDF + PNG binaries")]
    end

    TN --> A1 & A2 & A3 & A4 & A5 & A6 & A7 & A8 & A9
    A1 --> C1
    A2 --> C2
    A3 --> C3
    A4 --> C4
    A5 --> C5
    A6 --> C6
    A6 -.->|"pdf_file_id"| GFS
    A7 --> C7
    A8 & A9 --> C8
```

### 6.3 Key Document Shapes

**`services`** — topology graph
```json
{
  "service_id": "checkout-api",
  "environment": "production",
  "topology_version": "prod-2026-10-28",
  "depends_on": ["auth-service", "payment-gateway", "redis-cluster-east"],
  "criticality": "critical"
}
```

**`deployments`**
```json
{
  "deployment_id": "DEP-812",
  "pr_number": 812,
  "service_id": "auth-service",
  "deployed_at": "2026-10-28T13:58:00Z",
  "status": "rolled_back",
  "files_changed": ["config/redis.yaml"],
  "code_diff": "-  max_connections: 500\n+  max_connections: 50"
}
```

**`knowledge_chunks`** *(with embedding)*
```json
{
  "document_id": "KB-RUNBOOK-REDIS-001",
  "source_type": "runbook",
  "title": "Redis Connection Pool Exhaustion — Auth Service Runbook",
  "content": "When Redis pool saturation exceeds 90%...",
  "service_id": "auth-service",
  "embedding": [0.012, -0.034, "...1024 dims..."],
  "citation": { "file_name": "runbook_auth_redis.md", "line_start": 12 }
}
```

**`telemetry_events`**
```json
{
  "event_id": "TEL-2026-10-28-0401",
  "incident_id": "INC-2026-10-28-001",
  "service_id": "checkout-api",
  "timestamp": "2026-10-28T14:01:00Z",
  "metric_name": "http_504_rate_pct",
  "metric_value": 92.3,
  "severity": "critical",
  "message": "504 Gateway Timeout rate spiked to 92.3%"
}
```

**`sla_clauses`**
```json
{
  "clause_id": "SLA-ACME-4-2",
  "customer_id": "acme-corp",
  "clause_number": "4.2",
  "page": 4,
  "title": "P1 Incident Obligations — 15–30 Min Downtime",
  "downtime_min_minutes": 15,
  "downtime_max_minutes": 30,
  "financial_credit_pct": 0.0,
  "rca_required": true,
  "is_active": true
}
```

---

## 7. Search & Retrieval Architecture

### 7.1 Three-Stage Hybrid Search (Knowledge & Messages)

```mermaid
flowchart TD
    Q["Agent tool call with query string"]

    subgraph S1["Stage 1 — Broad Candidate Retrieval"]
        VS["$vectorSearch\nVoyage AI multimodal-3.5\n1024-dim cosine similarity\nnumCandidates = limit x 20"]
        BM25["$search BM25\nMongoDB Atlas Full-Text\nterm frequency + field boost\n(content, title)"]
        RF["Combine: $rankFusion native\nor RRF fallback\n60/40 vector/BM25 weights\ntop X = limit x 3 candidates"]
    end

    subgraph S2["Stage 2 — Precision Reranking"]
        RERANK["Voyage AI Reranker\nvoyage-rerank-2\nCross-encoder score\ntop Y = limit results"]
    end

    subgraph S3["Output"]
        EV["EvidenceItem list\nwith relevance_score\ncitation metadata\nclassification"]
    end

    Q --> VS & BM25
    VS & BM25 --> RF --> RERANK --> EV
```

**Why this three-stage approach:**

| Stage | Why Needed |
|---|---|
| **Vector search** | Captures semantic similarity — `"connection pool saturation"` matches `"max_connections exhausted"` |
| **BM25 keyword** | Handles exact technical terms — `PR #812`, `EVT-20261028-0401`, error codes |
| **$rankFusion** | Merges both ranked lists into a single relevance ordering, avoiding either signal dominating |
| **Voyage reranker** | Cross-encoder: reads query + document together, eliminating false positives from ANN retrieval — critical for evidence precision |

### 7.2 MongoDB Search Indexes Summary

| Collection | Vector Index | Text Index | Regular Indexes |
|---|---|---|---|
| `knowledge_chunks` | `vector_knowledge` (1024-dim cosine) | `text_knowledge` (content, title) | `service_id`, `source_type`, `incident_id` |
| `incident_messages` | `vector_messages` (1024-dim cosine) | `text_messages` (text, channel) | `incident_id` |
| `visual_evidence` | `vector_visual` (1024-dim cosine) | — | `incident_id` |
| `services` | — | — | `service_id + environment + topology_version` |
| `deployments` | — | — | `service_id + deployed_at` |
| `telemetry_events` | — | — | `service_id + timestamp` |
| `sla_clauses` | — | — | `customer_id + is_active` |

### 7.3 Topology Traversal — `$graphLookup`

Service dependencies are stored as a graph and queried with a single aggregation:

```javascript
// Find all services that checkout-api depends on (up to 4 hops deep)
db.services.aggregate([
  { $match: { service_id: "checkout-api", environment: "production" } },
  {
    $graphLookup: {
      from: "services",
      startWith: "$depends_on",
      connectFromField: "depends_on",
      connectToField: "service_id",
      as: "dependency_graph",
      maxDepth: 3,
      depthField: "depth"
    }
  }
])
// → { root: checkout-api, dependencies: [auth-service (depth 0), redis-cluster-east (depth 1), ...] }
```

---

## 8. Real-Time Streaming & Frontend

### 8.1 Frontend Component Map

```mermaid
flowchart TD
    subgraph Hooks["React Hooks"]
        UC["useChat()\nMessages · inspector state · sendMessage"]
        UIS["useInvestigationStream()\nSSE handler · toolExecutions · stage"]
        UT["useThreads()\nThread list · health check"]
    end

    subgraph Layout["AppLayout.tsx"]
        HDR["Header — incident badge · Open Inspector button"]
        SDB["Sidebar — investigation history list"]
        ASIDE["Inspector aside panel\ndesktop: CSS aside\nmobile: createPortal Drawer\n(JS isMobileView guard)"]
    end

    subgraph Chat["Chat Layer"]
        CW["ChatWindow"]
        CM["ChatMessage\nExamine Inspector button per message"]
        IA["InvestigationActivity\nReal-time tool pipeline cards"]
    end

    subgraph Inspector["Investigation Inspector (InvestigationReport.tsx)"]
        TAB1["Overview\nRootCause · Contradictions · SLA · Recommendations"]
        TAB2["Timeline — chronological event cards"]
        TAB3["Topology — D3 dependency graph"]
        TAB4["Evidence — EvidenceList + EvidenceCard\ndual verification badges"]
        TAB5["Visual — VisualEvidenceGallery\nGrafana screenshots"]
        TAB6["Telemetry — Recharts line series"]
        DRW["Evidence Drawer\nFull content · source/claim badges · citation"]
    end

    UC --> UIS
    UC --> Layout
    UIS -->|"toolExecutions[]"| IA
    CM -->|"openInspectorForMessage(result)"| ASIDE
    ASIDE --> Inspector
    TAB4 -->|"onViewDetails"| DRW
```

### 8.2 Investigation Activity Panel

The tool pipeline renders live tool execution status without any hardcoded counts:

- **"N tools executed"** badge: `toolExecutions.filter(t => t.status === 'completed').length` — dynamic count
- **Evidence badge** per tool: populated from `tool_completed` SSE event's `evidence_count` field
  - Backend distributes total `evidence_items` count proportionally across tools in each batch
- Tool cards **persist** after stream ends — `onDone` sweeps any `status === "running"` tools to `completed`
- Each tool card is **expandable** — shows summary text and start/end timestamps

### 8.3 Evidence Verification Dimensions

Each `EvidenceCard` in the Inspector shows two independent badges:

```
[✓ Source: Verified]  ← Did this record exist in MongoDB?
[Claim: Supported]    ← Does it support the RCA hypothesis?
```

Possible states:
- **Source**: `Verified` (green) | `Unavailable` (red)
- **Claim**: `Supported` (green) | `Partially Supported` (cyan) | `Contradicted` (red) | `Insufficient Evidence` (yellow)

---

## 9. Tech Stack

| Layer | Technology | Reason for Choice |
|---|---|---|
| **Frontend** | Next.js 14 App Router + TypeScript | SSE streaming support, type safety, server components |
| **Styling** | Tailwind CSS + custom dark theme | Rapid iteration, utility-first |
| **Charts** | Recharts | Telemetry series rendering |
| **Topology Graph** | D3.js | Force-directed service dependency visualization |
| **Backend** | FastAPI + Python 3.12 | Native `async` SSE streaming, fast iteration |
| **Agent Framework** | LangGraph | Stateful multi-node graph, conditional routing, persistent checkpointing |
| **LLM** | Google Gemini 2.5 Flash / OpenAI GPT-4.1 Mini | `with_structured_output()` for validated JSON, native tool calling |
| **Embeddings** | Voyage AI `voyage-multimodal-3.5` | Unified text + image embeddings, 1024 dimensions |
| **Reranker** | Voyage AI `voyage-rerank-2` | Cross-encoder reranking for evidence precision |
| **Database** | MongoDB Atlas Local (localhost:27017) | Vector search, BM25, `$graphLookup`, GridFS, and LangGraph checkpointing all in one system |
| **Vector Search** | MongoDB `$vectorSearch` + `$rankFusion` | No external vector DB needed — co-located with document store |
| **State Persistence** | MongoDB `MongoDBSaver` (LangGraph) | Persistent multi-turn agent memory across conversations |
| **Binary Storage** | MongoDB GridFS | SLA contract PDFs and Grafana screenshots |

---

## 10. Data Ingestion: Demo vs Production

### 10.1 Current: Seed Script (Demo Data)

For demonstration, all MongoDB data is created by `backend/data_layer/seed/seed_database.py`:

| Data Type | How Created | Volume |
|---|---|---|
| Incidents | Hand-authored JSON | 2 incidents |
| Services | Hand-authored topology | 6 microservices |
| Deployments | Synthetic PR records | ~10 records |
| Telemetry | Generated time-series metrics | ~50 events per incident window |
| Knowledge Chunks | Written runbooks, postmortems, PR diffs | ~20 documents |
| Slack Messages | Simulated war-room dialogue | ~30 messages per incident |
| SLA Clauses | Contract excerpt transcribed | 5 clauses for acme-corp |
| Visual Evidence | Sample Grafana-style PNG screenshots | 3 images in GridFS |

Voyage AI embeddings are generated at seed time and stored in-document (1024-dim vectors alongside text).

### 10.2 Production Integration Paths

```mermaid
flowchart LR
    subgraph Sources["Live Production Sources"]
        PD["PagerDuty / Jira\nIncident lifecycle"]
        GH["GitHub / GitLab\nPR merges · CI/CD deploys"]
        GR["Grafana / Datadog\nDashboard snapshots\nMetrics API"]
        SL["Slack Events API\nWar-room channels"]
        CF["Confluence / Notion\nRunbooks · Postmortems"]
        PDF["Legal / DocuSign\nSLA contract PDFs"]
        APM["Jaeger / Zipkin\nDistributed traces"]
    end

    subgraph Pipeline["Ingestion Pipeline"]
        WH["Webhooks\non incident open/update"]
        ETL["Nightly ETL batch\nfor historical data"]
        PP["PDF Chunker\npymupdf clause extraction"]
        VE["Voyage AI Encoder\ntext + multimodal embeddings"]
    end

    subgraph MongoDB["MongoDB"]
        COLS["All 10 Collections + GridFS"]
        IDX["Vector + Text + Regular Indexes"]
    end

    PD -->|webhook| WH --> COLS
    GH -->|webhook on PR merge| COLS
    GR -->|snapshot API| VE --> COLS
    SL -->|Events API| ETL --> COLS
    CF -->|sync| VE --> COLS
    PDF --> PP --> VE --> COLS
    APM -->|batch export| ETL --> COLS
    COLS --> IDX
```

**Key integration hooks for production:**
- **PagerDuty webhook** → auto-opens AegisRCA investigation thread on `incident.trigger`
- **GitHub Actions step** → push deployment record to MongoDB on every PR merge to main
- **Grafana snapshot API** → periodic screenshot ingestion with multimodal embeddings
- **Slack Events API** → stream war-room messages to `incident_messages` in real time
- **PDF chunker** (pymupdf) → parse SLA contracts into clause-level text chunks with page citations stored in GridFS

---

## 11. Project Structure

```
uncharted/
├── frontend/                          # Next.js 14 application
│   ├── app/
│   │   ├── chat/[threadId]/page.tsx   # Thread-specific investigation page
│   │   └── layout.tsx
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx         # Message list + streaming activity
│   │   │   ├── ChatMessage.tsx        # Message bubble + Examine Inspector
│   │   │   └── InvestigationActivity.tsx  # Real-time tool pipeline cards
│   │   ├── investigation/
│   │   │   ├── InvestigationReport.tsx    # Inspector tabs + Evidence Drawer
│   │   │   ├── EvidenceList.tsx           # Filter pills + evidence grid
│   │   │   ├── EvidenceCard.tsx           # Evidence card + verification badges
│   │   │   ├── IncidentTimeline.tsx       # Chronological event cards
│   │   │   ├── ServiceDependencyGraph.tsx # D3 topology force graph
│   │   │   ├── VisualEvidenceGallery.tsx  # Grafana screenshot gallery
│   │   │   └── SLAAssessment.tsx          # SLA verdict + clause display
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx         # Main layout + inspector panel/drawer
│   │   │   ├── Header.tsx
│   │   │   └── Sidebar.tsx
│   │   └── ui/                       # Badge, Button, Drawer, Modal, Loading
│   ├── hooks/
│   │   ├── useChat.ts                # Central: messages, inspector, sendMessage
│   │   ├── useInvestigationStream.ts # SSE handler → toolExecutions state
│   │   └── useThreads.ts
│   ├── lib/
│   │   ├── api.ts                    # streamMessage(), REST API calls
│   │   └── utils.ts                  # getToolInfo(), formatDate()
│   └── types/
│       ├── chat.ts                   # ChatMessage, ToolExecution
│       ├── investigation.ts          # InvestigationResult, EvidenceItem, Citation
│       └── api.ts                    # SSE payload type contracts
│
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── chat.py               # SSE stream endpoint
│   │   │   ├── evidence.py           # GridFS asset serving
│   │   │   └── health.py             # System health + connectivity check
│   │   ├── db/
│   │   │   ├── indexes.py            # MongoDB index definitions
│   │   │   ├── mongo.py              # Connection singleton + health check
│   │   │   └── repositories/        # thread, message, run, report repos
│   │   ├── graph/
│   │   │   ├── builder.py            # StateGraph + MongoDBSaver assembly
│   │   │   ├── state.py              # AgentState (MessagesState subclass)
│   │   │   ├── planner.py            # Intent classification node
│   │   │   ├── nodes.py              # agent_node + execute_tools
│   │   │   ├── verifier.py           # Evidence sufficiency evaluation
│   │   │   ├── report_generator.py   # Structured InvestigationReport synthesis
│   │   │   ├── routing.py            # Conditional edge router functions
│   │   │   └── llm_factory.py        # Gemini / OpenAI toggle
│   │   ├── prompts/
│   │   │   └── system_prompt.py      # AEGIS_RCA_SYSTEM_PROMPT
│   │   ├── schemas/
│   │   │   ├── investigation.py      # InvestigationReport, EvidenceItem, Citation
│   │   │   └── chat.py
│   │   ├── services/
│   │   │   ├── investigation_service.py  # SSE orchestration + LangGraph stream
│   │   │   ├── data_layer_adapter.py     # Raw data → EvidenceItem normalization
│   │   │   ├── evidence_service.py       # Citation validation + classification
│   │   │   ├── sla_service.py            # Deterministic SLA penalty calculator
│   │   │   ├── chat_service.py
│   │   │   └── thread_service.py
│   │   └── tools/
│   │       └── retrieval_tools.py        # 9 LangChain @tool wrappers
│   │
│   └── data_layer/                   # Standalone retrieval module
│       ├── retrieval.py              # All 9 retrieval functions + hybrid search
│       ├── embeddings.py             # Voyage AI embed_query + rerank_documents
│       ├── index_manager.py          # MongoDB Atlas index creation CLI
│       ├── schemas.py                # TypedDict document shape contracts
│       ├── mongo.py                  # PyMongo singleton
│       ├── config.py                 # Collection + index name constants
│       └── seed/                     # Demo data seeder script
│
└── infra/
    └── mongodb/
        ├── docker-compose.yml        # MongoDB Atlas Local container
        └── .env.example
```

---

## 12. Setup & Running

### Prerequisites
- Python 3.12+
- Node.js 18+ and pnpm
- Docker Desktop (for MongoDB Atlas Local)
- Voyage AI API key — [voyageai.com](https://www.voyageai.com)
- Google Gemini API key **or** OpenAI API key

### Step 1 — Start MongoDB Atlas Local

```bash
cd infra/mongodb
docker-compose up -d
# MongoDB: mongodb://aegisrca:dev-only-change-this@localhost:27017/?authSource=admin
```

### Step 2 — Seed the Database

```bash
cd backend/data_layer

# Configure ONLY the data_layer/.env (must point to localhost:27017)
cp .env.example .env
# Edit: set MONGODB_URI=mongodb://aegisrca:dev-only-change-this@localhost:27017/...
#       set VOYAGE_API_KEY=your_key

pip install -r requirements.txt
python -m seed.seed_database
# Creates all collections, generates 1024-dim embeddings, creates Atlas search indexes
```

### Step 3 — Start the Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate      # Linux/Mac
pip install -r requirements.txt

cp .env.example .env
# Edit: MONGODB_URI (localhost:27017), GEMINI_API_KEY or OPENAI_API_KEY, VOYAGE_API_KEY

uvicorn app.main:app --reload --port 8000
```

### Step 4 — Start the Frontend

```bash
cd frontend
pnpm install

# frontend/.env.local
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > .env.local

pnpm dev
# → http://localhost:3000
```

### Step 5 — Verify

Open [http://localhost:3000](http://localhost:3000). Bottom-left status shows:
- `MongoDBState` → **connected**
- `LangGraph Agent` → **initialized**
- `Data Layer` → **connected**

Try: *"Why did Checkout API fail between 14:00 and 14:25 UTC on 2026-10-28?"*

---

## 13. MongoDB Collections & Indexes

```mermaid
erDiagram
    incidents ||--o{ telemetry_events : "incident_id"
    incidents ||--o{ incident_messages : "incident_id"
    incidents ||--o{ visual_evidence : "incident_id"
    incidents ||--o{ deployments : "service_id + time window"
    incidents ||--o{ knowledge_chunks : "incident_id (optional)"
    services ||--o{ services : "depends_on self-ref graph"
    sla_clauses }|--|| incidents : "customer_id"
    investigation_runs ||--o{ chat_messages : "run_id"
    langgraph_checkpoints ||--o{ investigation_runs : "thread_id"

    incidents {
        string incident_id PK
        string status
        string severity
        string customer_id
        string start_time
        int downtime_minutes
    }
    services {
        string service_id PK
        string topology_version
        array depends_on
        string environment
    }
    knowledge_chunks {
        string document_id PK
        string source_type
        string content
        array embedding "1024-dim"
        dict citation
    }
    deployments {
        string deployment_id PK
        int pr_number
        string service_id
        string deployed_at
        string code_diff
    }
    sla_clauses {
        string clause_id PK
        string customer_id
        string clause_number
        int page
        float financial_credit_pct
        bool rca_required
    }
```

---

## 14. Environment Configuration

### `backend/.env`

```env
# MongoDB — MUST be localhost for local dev
MONGODB_URI=mongodb://aegisrca:dev-only-change-this@localhost:27017/?authSource=admin&directConnection=true
MONGODB_DB_NAME=aegisrca

# LLM provider (pick one)
USE_OPENAI=false
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-2.5-flash

OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4.1-mini

# Embeddings + reranker
VOYAGE_API_KEY=your_voyage_key_here

# Agent tuning
MAX_TOOL_ITERATIONS=6         # Max rounds of tool calling per investigation
MAX_TOOLS_PER_TURN=10         # Max concurrent tool calls per agent turn
MAX_VERIFICATION_ATTEMPTS=1   # Max verifier retries before forcing report generation
MAX_HISTORY_MESSAGES=20       # LLM context window: max messages to include
```

### `backend/data_layer/.env`

```env
# IMPORTANT: Must also point to localhost:27017 — NOT Atlas cloud
# The data layer has its own config.py and loads this .env independently
MONGODB_URI=mongodb://aegisrca:dev-only-change-this@localhost:27017/?authSource=admin&directConnection=true
MONGODB_DB_NAME=aegisrca

VOYAGE_API_KEY=your_voyage_key_here
VOYAGE_MODEL=voyage-multimodal-3.5
EMBEDDING_DIMENSIONS=1024
```

### `frontend/.env.local`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> **Important:** Both `backend/.env` and `backend/data_layer/.env` must point to the **same MongoDB instance**. A mismatch (e.g., data layer pointing to Atlas cloud while backend points to localhost) causes all tool retrieval calls to fail silently with DNS resolution errors — the agent will return `INSUFFICIENT_EVIDENCE` with an empty evidence list even though tools appear to execute.

---

*AegisRCA — Autonomous incident investigation for SRE teams.*

