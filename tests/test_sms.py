from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def make_mock_anthropic_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    return response


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.services.llm.anthropic.Anthropic")
def test_receive_sms(mock_anthropic_cls):
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


def test_receive_sms_missing_fields():
    response = client.post("/sms", json={"sender": "+1234567890"})
    assert response.status_code == 422


@patch("app.routers.sms.TWILIO_AUTH_TOKEN", "")
@patch("app.services.llm.anthropic.Anthropic")
def test_twilio_webhook_returns_twiml(mock_anthropic_cls):
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    mock_client.messages.create.return_value = make_mock_anthropic_response(
        "Checking your inbox now."
    )

    response = client.post(
        "/sms/twilio",
        data={"Body": "read inbox", "From": "+1234567890", "To": "+10987654321"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/xml"
    assert "<Message>" in response.text
    assert "Checking your inbox now." in response.text


@patch("app.routers.sms.TWILIO_AUTH_TOKEN", "test-auth-token")
@patch("app.routers.sms.RequestValidator")
def test_twilio_webhook_rejects_invalid_signature(mock_validator_cls):
    mock_validator = MagicMock()
    mock_validator_cls.return_value = mock_validator
    mock_validator.validate.return_value = False

    response = client.post(
        "/sms/twilio",
        data={"Body": "read inbox", "From": "+1234567890", "To": "+10987654321"},
    )
    assert response.status_code == 403
