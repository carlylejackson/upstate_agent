def test_health(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_hours_query_deterministic(client):
    session = client.post("/v1/chat/session", json={"channel": "web"}).json()
    response = client.post(
        "/v1/chat/message",
        json={"session_id": session["session_id"], "channel": "web", "text": "What are your business hours?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "hours_location_contact"
    assert "Monday-Friday 9:00 AM-4:00 PM ET" in body["response_text"]


def test_emergency_query_escalates(client):
    session = client.post("/v1/chat/session", json={"channel": "web"}).json()
    response = client.post(
        "/v1/chat/message",
        json={
            "session_id": session["session_id"],
            "channel": "web",
            "text": "I have chest pain and severe dizziness right now",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is True
    assert "urgent" in body["response_text"].lower() or "911" in body["response_text"]


def test_unknown_query_escalates(client):
    session = client.post("/v1/chat/session", json={"channel": "web"}).json()
    response = client.post(
        "/v1/chat/message",
        json={"session_id": session["session_id"], "channel": "web", "text": "Tell me your latest cortical adaptation index"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is True


def test_admin_policy_requires_key(client):
    response = client.post(
        "/v1/admin/policy",
        json={"policy_key": "phone", "policy_value": "(111) 222-3333", "updated_by": "test"},
    )
    assert response.status_code == 401


def test_admin_policy_update_with_key(client):
    response = client.post(
        "/v1/admin/policy",
        headers={"X-Admin-Key": "test-admin-key"},
        json={"policy_key": "phone", "policy_value": "(111) 222-3333", "updated_by": "test"},
    )
    assert response.status_code == 200

    session = client.post("/v1/chat/session", json={"channel": "web"}).json()
    follow_up = client.post(
        "/v1/chat/message",
        json={"session_id": session["session_id"], "channel": "web", "text": "what is your phone number?"},
    )
    assert follow_up.status_code == 200
    assert "(111) 222-3333" in follow_up.json()["response_text"]


def test_sms_webhook_returns_twiml(client):
    response = client.post(
        "/v1/sms/webhook/twilio",
        data={"From": "+18645551234", "Body": "What are your hours?"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    assert "<Response>" in response.text


def test_appointment_lead_capture_flow(client):
    session = client.post(
        "/v1/chat/session",
        json={"channel": "web", "consent_to_contact": True},
    ).json()
    response = client.post(
        "/v1/chat/message",
        json={
            "session_id": session["session_id"],
            "channel": "web",
            "text": "I need an appointment. You can reach me at 864-770-8822",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "appointment_request"
