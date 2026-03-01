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


def test_non_phi_medical_query_short_circuits(client):
    session = client.post("/v1/chat/session", json={"channel": "web"}).json()
    response = client.post(
        "/v1/chat/message",
        json={
            "session_id": session["session_id"],
            "channel": "web",
            "text": "I have worsening tinnitus and dizziness for three days",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is True
    assert "privacy and safety" in body["response_text"].lower()


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


def test_sms_appointment_consent_wording(client):
    session = client.post(
        "/v1/chat/session",
        json={"channel": "sms", "consent_to_contact": True},
    ).json()
    response = client.post(
        "/v1/chat/message",
        json={
            "session_id": session["session_id"],
            "channel": "sms",
            "text": "I need to schedule an appointment",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "appointment_request"
    assert "consent" in body["response_text"].lower()


def test_inbound_message_is_redacted_in_storage(client):
    session = client.post("/v1/chat/session", json={"channel": "web"}).json()
    response = client.post(
        "/v1/chat/message",
        json={
            "session_id": session["session_id"],
            "channel": "web",
            "text": "My email is test@example.com and phone is 864-770-8822",
        },
    )
    assert response.status_code == 200

    from app.db.models import ConversationMessage
    from app.db.session import get_session_factory

    db = get_session_factory()()
    try:
        msg = (
            db.query(ConversationMessage)
            .filter(
                ConversationMessage.session_id == session["session_id"],
                ConversationMessage.role == "user",
            )
            .order_by(ConversationMessage.id.desc())
            .first()
        )
        assert msg is not None
        assert "[REDACTED_EMAIL]" in msg.text
        assert "[REDACTED_PHONE]" in msg.text
    finally:
        db.close()


def test_retention_run_endpoint_dry_run_and_execute(client):
    from datetime import datetime, timedelta, timezone

    from app.db.models import ConversationMessage, ConversationSession, EscalationTicket
    from app.db.session import get_session_factory

    db = get_session_factory()()
    try:
        session = ConversationSession(channel="web")
        db.add(session)
        db.commit()
        db.refresh(session)

        old_ts = datetime.now(timezone.utc) - timedelta(days=400)
        db.add(
            ConversationMessage(
                session_id=session.id,
                channel="web",
                role="user",
                text="old message",
                created_at=old_ts,
            )
        )
        db.add(
            EscalationTicket(
                session_id=session.id,
                channel="web",
                reason="test",
                status="resolved",
                conversation_excerpt="old escalation",
                created_at=old_ts,
            )
        )
        db.commit()
    finally:
        db.close()

    dry = client.post(
        "/v1/admin/privacy/retention-run",
        headers={"X-Admin-Key": "test-admin-key"},
        json={"dry_run": True, "updated_by": "test"},
    )
    assert dry.status_code == 200
    dry_body = dry.json()
    assert dry_body["messages_to_delete"] >= 1
    assert dry_body["escalations_to_delete"] >= 1
    assert dry_body["deleted_messages"] == 0
    assert dry_body["deleted_escalations"] == 0

    run = client.post(
        "/v1/admin/privacy/retention-run",
        headers={"X-Admin-Key": "test-admin-key"},
        json={"dry_run": False, "updated_by": "test"},
    )
    assert run.status_code == 200
    run_body = run.json()
    assert run_body["deleted_messages"] >= 1
    assert run_body["deleted_escalations"] >= 1
