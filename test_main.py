import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_receive_sms():
    payload = {"sender": "+1234567890", "message": "read inbox"}
    response = client.post("/sms", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["received_from"] == "+1234567890"
    assert data["message"] == "read inbox"
    assert data["status"] == "received"


def test_receive_sms_missing_fields():
    response = client.post("/sms", json={"sender": "+1234567890"})
    assert response.status_code == 422
