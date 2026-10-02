import pytest
from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)

def test_dashboard_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Local Coding Agent Dashboard" in response.text
    assert "initConnection()" in response.text

def test_stream_api_endpoint():
    response = client.post(
        "/api/stream",
        json={
            "user_input": "Hello",
            "api_key": "test_key",
            "provider": "gemini",
            "model": "gemini-2.0-flash"
        }
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
