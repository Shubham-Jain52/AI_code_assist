
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import json
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

# Mock Redis before client creation might be needed, 
# but getting client happens at import time in main.py.
# So we need to patch specifically where it's used.

@pytest.fixture
def mock_redis():
    with patch("api.main.redis_client") as mock:
        yield mock

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    # Should be the index.html content (checking generic match)
    assert "text/html" in response.headers["content-type"]

def test_submit_review(mock_redis):
    payload = {"diff": "print('hello')", "language": "python"}
    response = client.post("/review", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "submission_id" in data
    assert data["status"] == "queued"
    
    # Verify Redis interactions
    # 1. HSET called to set status
    mock_redis.hset.assert_called()
    # 2. RPUSH called to add to queue
    mock_redis.rpush.assert_called()

def test_get_status_pending(mock_redis):
    # Mock Redis return for HGETALL
    submission_id = "test-123"
    mock_redis.hgetall.return_value = {
        "submission_id": submission_id,
        "status": "pending"
    }
    
    response = client.get(f"/status/{submission_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["risk_score"] == 0

def test_get_status_completed(mock_redis):
    submission_id = "test-done"
    mock_redis.hgetall.return_value = {
        "submission_id": submission_id,
        "status": "completed",
        "risk_score": "80",
        "quality_score": "20",
        "comments": '["Error 1"]',
        "flags": '["Flag 1"]'
    }
    
    response = client.get(f"/status/{submission_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["risk_score"] == 80
    assert data["flags"] == ["Flag 1"]

def test_get_status_not_found(mock_redis):
    mock_redis.hgetall.return_value = {}
    
    response = client.get("/status/non-existent")
    assert response.status_code == 404
