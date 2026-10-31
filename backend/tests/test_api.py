"""API integration tests for FastAPI endpoints."""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify GET /health returns expected schema."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "mongodb" in data
    assert "agent" in data
    assert "data_layer" in data


def test_thread_crud_endpoints():
    """Verify thread creation, listing, retrieval, and deletion."""
    # 1. Create thread
    create_resp = client.post("/api/chat/threads", json={"title": "API Test Outage"})
    assert create_resp.status_code == 201
    thread_data = create_resp.json()
    thread_id = thread_data["thread_id"]
    assert thread_data["title"] == "API Test Outage"

    # 2. Get thread
    get_resp = client.get(f"/api/chat/threads/{thread_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["thread_id"] == thread_id

    # 3. List threads
    list_resp = client.get("/api/chat/threads")
    assert list_resp.status_code == 200
    assert "threads" in list_resp.json()

    # 4. Get thread messages
    msgs_resp = client.get(f"/api/chat/threads/{thread_id}/messages")
    assert msgs_resp.status_code == 200
    assert msgs_resp.json()["thread_id"] == thread_id

    # 5. Delete thread
    del_resp = client.delete(f"/api/chat/threads/{thread_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"


def test_evidence_asset_not_found():
    """Verify 404/501 handling for nonexistent or pending visual assets."""
    resp = client.get("/api/evidence/assets/nonexistent_file_id")
    assert resp.status_code in [404, 501]

