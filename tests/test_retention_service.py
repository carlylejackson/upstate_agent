import os
from datetime import datetime, timedelta, timezone


def _reset_runtime():
    from app.core.config import get_settings
    from app.db.session import get_engine, get_session_factory

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def test_retention_service_dry_run_and_execute(tmp_path):
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'retention_unit.db'}"
    os.environ["RETENTION_DAYS_MESSAGES"] = "30"
    os.environ["RETENTION_DAYS_ESCALATIONS"] = "90"
    _reset_runtime()

    from app.db.init_db import init_db
    from app.db.models import ConversationMessage, ConversationSession, EscalationTicket
    from app.db.session import get_session_factory
    from app.services.retention_service import RetentionService

    db = get_session_factory()()
    try:
        init_db(db)
        session = ConversationSession(channel="web")
        db.add(session)
        db.commit()
        db.refresh(session)

        old_ts = datetime.now(timezone.utc) - timedelta(days=365)
        db.add(ConversationMessage(session_id=session.id, channel="web", role="user", text="old", created_at=old_ts))
        db.add(
            EscalationTicket(
                session_id=session.id,
                channel="web",
                reason="old",
                conversation_excerpt="old excerpt",
                status="resolved",
                created_at=old_ts,
            )
        )
        db.commit()

        service = RetentionService(db)
        dry = service.run_cleanup(updated_by="unit-test", dry_run=True)
        assert dry["messages_to_delete"] >= 1
        assert dry["escalations_to_delete"] >= 1
        assert dry["deleted_messages"] == 0
        assert dry["deleted_escalations"] == 0

        run = service.run_cleanup(updated_by="unit-test", dry_run=False)
        assert run["deleted_messages"] >= 1
        assert run["deleted_escalations"] >= 1
    finally:
        db.close()
