# AegisRCA — Data Layer

Member 1 implementation: synthetic data generation, MongoDB storage, indexing, and retrieval for the AegisRCA root-cause-analysis system.

---

## Quick-Start

```bash
# 1. Clone the repo and cd into the backend
cd AegisRCA/backend

# 2. Create venv and install deps
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS
pip install -r data_layer/requirements.txt

# 3. Start MongoDB (Atlas Local — supports $vectorSearch, $search, $rankFusion)
docker compose -f ../infra/mongodb/docker-compose.yml up -d

# 4. Copy env file and fill in your Voyage AI key
copy data_layer\.env.example data_layer\.env
# Edit data_layer/.env and set VOYAGE_API_KEY

# 5. Seed the database
python -m data_layer.seed.seed_database

# 6. Run tests
pytest data_layer/tests/ -v

# 7. Run smoke test
python -m data_layer.tests.smoke_test
```

### Skip-embeddings mode (no Voyage API key needed)

```bash
python -m data_layer.seed.seed_database --skip-embeddings
```

Graph, structured and keyword search all work. Only `$vectorSearch` and `$rankFusion` are disabled.

### Full reset + reseed

```bash
python -m data_layer.seed.seed_database --reset
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `MONGODB_URI` | PyMongo connection string | `mongodb://aegisrca:dev-only-change-this@localhost:27017/?authSource=admin&directConnection=true` |
| `MONGODB_DB_NAME` | Database name | `aegisrca` |
| `VOYAGE_API_KEY` | Voyage AI API key | *(required for embeddings)* |
| `VOYAGE_MODEL` | Embedding model | `voyage-multimodal-3.5` |
| `EMBEDDING_DIMENSIONS` | Vector dimensions | `1024` |

---

## Database: `aegisrca`

### Collections

| Collection | Contents | Key query method |
|---|---|---|
| `services` | 8 microservice definitions + dependency graph | `$graphLookup` |
| `deployments` | 9 deployment / PR records | structured filter |
| `knowledge_chunks` | Chunked PR diffs, runbooks, postmortems, SLA text | `$vectorSearch` + `$search` + `$rankFusion` |
| `telemetry_events` | 180 structured metrics/logs | compound index filter |
| `incident_messages` | 50 Slack messages | `$vectorSearch` + `$search` + `$rankFusion` |
| `sla_clauses` | Structured SLA threshold records | exact filter |
| `visual_evidence` | Grafana screenshot metadata + multimodal embeddings | `$vectorSearch` |
| `incidents` | Main incident record | `_id` / `incident_id` |
| `investigation_reports` | Reserved for Member 2 generated reports | `incident_id` index |

### GridFS

Binary PDFs and PNGs are stored in GridFS (`fs.files` / `fs.chunks`).  
Retrieve with `get_visual_asset(file_id)`.

---

## Search Index Names

| Index name | Collection | Type |
|---|---|---|
| `knowledge_vector_idx` | `knowledge_chunks` | Vector Search (cosine, 1024-dim) |
| `messages_vector_idx` | `incident_messages` | Vector Search (cosine, 1024-dim) |
| `visual_vector_idx` | `visual_evidence` | Vector Search (cosine, 1024-dim) |
| `knowledge_text_idx` | `knowledge_chunks` | Atlas Search (BM25) |
| `messages_text_idx` | `incident_messages` | Atlas Search (BM25) |

> **Note:** `$rankFusion` requires MongoDB ≥ 8.0.  
> The `mongodb/mongodb-atlas-local:8.0.4` image in `infra/mongodb/docker-compose.yml` satisfies this.

---

## Integration: Member 2 Import API

```python
from data_layer import (
    get_dependency_chain,   # $graphLookup service traversal
    search_knowledge,       # hybrid vector+BM25 over PR diffs, runbooks, postmortems, SLAs
    query_telemetry,        # structured time-range filter on telemetry_events
    search_messages,        # hybrid vector+BM25 over Slack messages
    search_sla,             # deterministic SLA clause retrieval
    get_deployments,        # deployment records for a service
    get_incident,           # single incident by ID
    list_incidents,         # list incidents by date/status
    search_visual_evidence, # multimodal vector search over screenshots
    get_visual_asset,       # raw PNG/JPEG bytes from GridFS
)
```

All functions return **plain JSON-serialisable dicts/lists**.  
No raw ObjectId, datetime, binary or embedding arrays are ever returned.

### Function Signatures

```python
def get_dependency_chain(
    service_id: str,
    environment: str = "production",
    topology_version: str = "prod-2026-10-28",
    max_depth: int = 4,
) -> dict:
    # Returns: {"root": {...}, "dependencies": [{..., "depth": int}, ...]}

def search_knowledge(
    query: str,
    filters: dict | None = None,   # keys: source_type, service_id, incident_id, customer_id, environment
    limit: int = 5,
) -> list[dict]:
    # Returns: [{document_id, source_id, source_type, source_file, title,
    #             content, service_id, incident_id, customer_id, timestamp, citation, score}]

def query_telemetry(
    service_id: str,
    start=None,   # datetime or ISO-8601 string
    end=None,
) -> list[dict]:

def search_messages(
    query: str,
    incident_id: str | None = None,
    limit: int = 10,
) -> list[dict]:

def search_sla(customer_id: str) -> list[dict]:
    # Returns all active SLA clauses with structured threshold fields

def get_deployments(service_id: str, start=None, end=None) -> list[dict]:

def get_incident(incident_id: str) -> dict | None:

def list_incidents(date=None, status: str | None = None) -> list[dict]:

def search_visual_evidence(
    query: str,
    incident_id: str | None = None,
    limit: int = 3,
) -> list[dict]:

def get_visual_asset(file_id: str) -> bytes | None:
```

### Example return — `search_knowledge`

```json
{
  "document_id": "chunk-pr-812",
  "source_id": "PR-812",
  "source_type": "pr_diff",
  "source_file": "GitHub_PR_812.json",
  "title": "PR #812: Tune Redis connection pool for cost optimisation...",
  "content": "PR #812: ... redis_pool_max_connections changed 500 → 50 ...",
  "service_id": "auth-service",
  "incident_id": "INC-2026-10-28-001",
  "customer_id": null,
  "timestamp": "2026-10-28T13:58:00Z",
  "citation": {
    "file_name": "GitHub_PR_812.json",
    "line_start": 44,
    "line_end": 48,
    "page": null
  },
  "score": 0.9412
}
```

---

## Embedding Status

After seeding, call:

```python
from data_layer.config import cfg
from data_layer.mongo import get_db
db = get_db()
has_embeddings = db[cfg.col_knowledge].find_one({"embedding": {"$ne": None}}) is not None
print("Embeddings available:", has_embeddings)
```

If `False`, only graph, structured and keyword (`$search`) retrieval works.  
Semantic (`$vectorSearch`) and multimodal retrieval will raise `RuntimeError` with a clear message.

---

## Known Limitations

- `$rankFusion` requires MongoDB 8.0+. On older versions, the code falls back to `$vectorSearch` only with a logged warning.
- Atlas Search indexes (text + vector) take 30–300 seconds to become `READY` after creation. The seed script waits automatically.
- The Voyage AI `multimodal_embed()` API is called with `input_type="document"` for stored content and `"query"` for searches. Both must use the same model.
- Raw telemetry events do **not** have embeddings — use `query_telemetry()` (structured filter) for telemetry, not `search_knowledge()`.

---

## File Structure

```
backend/data_layer/
├── __init__.py          ← public import surface (Member 2 uses this)
├── config.py            ← env var loading
├── mongo.py             ← singleton PyMongo client
├── schemas.py           ← TypedDicts documenting document shapes
├── embeddings.py        ← Voyage AI embedding helpers
├── index_manager.py     ← creates/verifies all MongoDB indexes
├── retrieval.py         ← ALL retrieval functions
│
├── seed/
│   ├── scenario.py          ← single source of truth (IDs, timestamps, figures)
│   ├── generate_dataset.py  ← services, deployments, messages, telemetry, runbooks, SLA data
│   ├── generate_assets.py   ← PDF generation (ReportLab), PNG generation (Matplotlib)
│   ├── seed_database.py     ← master seeding script
│   └── expected_results.json ← ground-truth fixture (NOT in MongoDB)
│
└── tests/
    ├── test_dataset.py       ← collection count + referential integrity tests
    ├── test_retrieval.py     ← retrieval function tests (semantic tests auto-skip w/o embeddings)
    └── smoke_test.py         ← quick connectivity + basic retrieval smoke test
```

---

## Docker Commands

```bash
# Start
docker compose -f infra/mongodb/docker-compose.yml up -d

# Stop
docker compose -f infra/mongodb/docker-compose.yml down

# Logs
docker compose -f infra/mongodb/docker-compose.yml logs -f mongodb

# Open mongosh
docker exec -it aegisrca-mongo mongosh \
  --username aegisrca --password dev-only-change-this \
  --authenticationDatabase admin

# Full reset (deletes all data volumes)
docker compose -f infra/mongodb/docker-compose.yml down -v
```

> ⚠️ Credentials `aegisrca / dev-only-change-this` are for **local development only**. Change before any deployment.

