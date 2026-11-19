"""End-to-end HTTP boundary and API endpoint tests."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_validation_boundary_422_on_bad_image(client):
    # Missing required 'url' and 'filename' fields
    response = client.post("/api/images", json={"invalid_field": "data"})
    assert response.status_code == 422
    assert response.json()["error"] == "Validation Error"

def test_validation_boundary_422_on_bad_post(client):
    # Content too short (< 10 chars)
    response = client.post("/api/posts", json={"title": "Short", "content": "too few"})
    assert response.status_code == 422

def test_post_suggestions_flow(client):
    # Fetch suggestions for seeded fox post
    response = client.get("/api/posts/post_fox_01/suggestions")
    assert response.status_code == 200
    data = response.json()
    assert data["post_id"] == "post_fox_01"
    assert data["status"] == "MATCH_FOUND"
    assert data["top_recommendation"]["image_id"] == "img_fox_01"
    assert data["top_recommendation"]["guard_decision"] == "ACCEPTED"

def test_post_suggestions_404_on_missing_post(client):
    response = client.get("/api/posts/nonexistent_post_xyz/suggestions")
    assert response.status_code == 404

def test_human_review_workflow(client):
    # Get a suggestion id
    sug_resp = client.get("/api/posts/post_fox_01/suggestions").json()
    sug_id = sug_resp["top_recommendation"]["id"]

    # Approve
    review_resp = client.post("/api/reviews", json={
        "suggestion_id": sug_id,
        "decision": "APPROVED",
        "reviewer_notes": "Perfect match verified by editorial team"
    })
    assert review_resp.status_code == 201
    assert review_resp.json()["decision"] == "APPROVED"

    # List history
    history = client.get("/api/reviews").json()
    assert len(history) > 0
    assert history[0]["suggestion_id"] == sug_id

def test_cost_telemetry_endpoints(client):
    summary = client.get("/api/costs/summary").json()
    assert "total_calls" in summary
    assert "total_cost_usd" in summary

    log = client.get("/api/costs/log").json()
    assert isinstance(log, list)

def test_evaluation_api_endpoint(client):
    eval_resp = client.get("/api/eval/latest")
    assert eval_resp.status_code == 200
    data = eval_resp.json()
    assert data["headline_metrics"]["top1_precision"] >= 0.90
