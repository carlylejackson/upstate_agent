import os


def _reset_runtime():
    from app.core.config import get_settings
    from app.db.session import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def test_escalation_email_omits_excerpt_by_default(tmp_path, monkeypatch):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'escalation_email_default.db'}"
    os.environ["ESCALATION_EMAIL_INCLUDE_EXCERPT"] = "false"
    _reset_runtime()

    sent: dict[str, str] = {}

    def _capture_send(self, subject: str, body: str, to_address: str | None = None) -> None:  # noqa: ANN001
        sent["subject"] = subject
        sent["body"] = body

    from app.db.init_db import init_db
    from app.db.models import EscalationTicket
    from app.db.session import get_session_factory
    from app.integrations.email_client import EmailClient
    from app.services.escalation_service import EscalationService

    monkeypatch.setattr(EmailClient, "send", _capture_send)

    db = get_session_factory()()
    try:
        init_db(db)
        ticket = EscalationService(db).create_ticket(
            session_id="s1",
            channel="web",
            reason="phase1_non_phi_restriction",
            conversation_excerpt="I have dizziness and my email is test@example.com",
            priority="medium",
        )
        stored = db.query(EscalationTicket).filter(EscalationTicket.id == ticket.id).first()
    finally:
        db.close()

    assert "subject" in sent
    assert "Excerpt omitted by policy." in sent["body"]
    assert "Excerpt (redacted):" not in sent["body"]
    assert "test@example.com" not in sent["body"]
    assert stored is not None
    assert "[REDACTED_EMAIL]" in stored.conversation_excerpt


def test_escalation_email_optional_excerpt_is_redacted_and_truncated(tmp_path, monkeypatch):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'escalation_email_enabled.db'}"
    os.environ["ESCALATION_EMAIL_INCLUDE_EXCERPT"] = "true"
    os.environ["ESCALATION_EMAIL_EXCERPT_MAX_CHARS"] = "40"
    _reset_runtime()

    sent: dict[str, str] = {}

    def _capture_send(self, subject: str, body: str, to_address: str | None = None) -> None:  # noqa: ANN001
        sent["subject"] = subject
        sent["body"] = body

    from app.db.init_db import init_db
    from app.db.models import EscalationTicket
    from app.db.session import get_session_factory
    from app.integrations.email_client import EmailClient
    from app.services.escalation_service import EscalationService

    monkeypatch.setattr(EmailClient, "send", _capture_send)

    long_text = "My email is user@example.com and phone 864-770-8822. " + ("x" * 200)

    db = get_session_factory()()
    try:
        init_db(db)
        ticket = EscalationService(db).create_ticket(
            session_id="s2",
            channel="web",
            reason="manual_review",
            conversation_excerpt=long_text,
            priority="high",
        )
        stored = db.query(EscalationTicket).filter(EscalationTicket.id == ticket.id).first()
    finally:
        db.close()

    assert "Excerpt (redacted):" in sent["body"]
    assert "user@example.com" not in sent["body"]
    assert "864-770-8822" not in sent["body"]
    excerpt = sent["body"].split("Excerpt (redacted):\n", maxsplit=1)[1]
    assert len(excerpt) <= 40
    assert stored is not None
    assert "user@example.com" not in stored.conversation_excerpt
    assert "864-770-8822" not in stored.conversation_excerpt
    assert "[REDACTED_EMAIL]" in stored.conversation_excerpt
    assert "[REDACTED_PHONE]" in stored.conversation_excerpt
