import os


def test_root_and_chat_test_page(client):
    root = client.get("/")
    assert root.status_code == 200
    assert root.json()["name"] == "Upstate Agent API"

    page = client.get("/chat-test")
    assert page.status_code == 200
    assert "Upstate Agent Chat Test" in page.text


def test_metrics_endpoint(client):
    metrics = client.get("/v1/metrics")
    assert metrics.status_code == 200
    payload = metrics.json()
    assert "sessions_total" in payload
    assert "messages_total" in payload
    assert "escalations_open" in payload


def test_e2e_chat_flow_updates_metrics(client):
    before = client.get("/v1/metrics").json()
    session = client.post("/v1/chat/session", json={"channel": "web"}).json()
    response = client.post(
        "/v1/chat/message",
        json={
            "session_id": session["session_id"],
            "channel": "web",
            "text": "What are your business hours?",
        },
    )
    assert response.status_code == 200

    after = client.get("/v1/metrics").json()
    assert after["sessions_total"] >= before["sessions_total"]
    assert after["messages_total"] >= before["messages_total"] + 2


def test_sms_signature_validation_enforced_when_enabled(client):
    from app.core.config import get_settings

    os.environ["TWILIO_VALIDATE_SIGNATURES"] = "true"
    get_settings.cache_clear()

    response = client.post(
        "/v1/sms/webhook/twilio",
        data={"From": "+18645551234", "Body": "What are your hours?"},
    )
    assert response.status_code == 401

    os.environ["TWILIO_VALIDATE_SIGNATURES"] = "false"
    get_settings.cache_clear()


def test_sms_signature_validation_accepts_valid_signature(client):
    from app.core.config import get_settings
    from app.integrations.twilio_security import compute_twilio_signature

    os.environ["TWILIO_VALIDATE_SIGNATURES"] = "true"
    os.environ["TWILIO_AUTH_TOKEN"] = "test-token"
    get_settings.cache_clear()

    url = "http://testserver/v1/sms/webhook/twilio"
    params = {"From": "+18645551234", "Body": "What are your hours?"}
    sig = compute_twilio_signature(url, params, "test-token")

    response = client.post(
        "/v1/sms/webhook/twilio",
        data=params,
        headers={"X-Twilio-Signature": sig},
    )
    assert response.status_code == 200
    assert "<Response>" in response.text

    os.environ["TWILIO_VALIDATE_SIGNATURES"] = "false"
    get_settings.cache_clear()
