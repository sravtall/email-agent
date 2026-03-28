from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def make_mock_anthropic_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text

    response = MagicMock()
    response.content = [block]
    return response


@patch("main.os.getenv", return_value="fake-api-key")
@patch("main.anthropic.Anthropic")
def test_receive_sms(mock_anthropic_cls, mock_getenv):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = make_mock_anthropic_response(
        "I would read your inbox and summarize the latest emails."
    )

    response = client.post("/sms", json={"sender": "+1234567890", "message": "read inbox"})
    assert response.status_code == 200
    data = response.json()
    assert data["received_from"] == "+1234567890"
    assert data["message"] == "read inbox"
    assert data["status"] == "processed"
    assert "reply" in data


@patch("main.os.getenv", return_value=None)
def test_receive_sms_missing_api_key(mock_getenv):
    response = client.post("/sms", json={"sender": "+1234567890", "message": "read inbox"})
    assert response.status_code == 500


def test_receive_sms_missing_fields():
    response = client.post("/sms", json={"sender": "+1234567890"})
    assert response.status_code == 422
