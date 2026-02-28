import os

from fastapi.testclient import TestClient


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


def test_rate_limit_enforced_for_non_exempt_path(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'rate_limit.db'}"
    os.environ["RATE_LIMIT_ENABLED"] = "true"
    os.environ["RATE_LIMIT_REQUESTS_PER_MINUTE"] = "2"
    os.environ["RATE_LIMIT_EXEMPT_PATHS"] = "/v1/health,/v1/metrics"

    from app.core.config import get_settings
    from app.db.session import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as local_client:
        first = local_client.post("/v1/chat/session", json={"channel": "web"})
        second = local_client.post("/v1/chat/session", json={"channel": "web"})
        third = local_client.post("/v1/chat/session", json={"channel": "web"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429


def test_cors_allowlist_applies_in_production(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'cors.db'}"
    os.environ["APP_ENV"] = "production"
    os.environ["CORS_ORIGINS"] = "https://www.upstatehearingandbalance.com"

    from app.core.config import get_settings
    from app.db.session import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as local_client:
        response = local_client.options(
            "/v1/health",
            headers={
                "Origin": "https://www.upstatehearingandbalance.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://www.upstatehearingandbalance.com"
