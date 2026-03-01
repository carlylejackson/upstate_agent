from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AuditLog, ConversationMessage, EscalationTicket


class RetentionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def run_cleanup(self, updated_by: str, dry_run: bool = False) -> dict:
        now = datetime.now(timezone.utc)
        message_cutoff = now - timedelta(days=max(self.settings.retention_days_messages, 1))
        escalation_cutoff = now - timedelta(days=max(self.settings.retention_days_escalations, 1))

        messages_to_delete = self.db.scalar(
            select(func.count()).select_from(ConversationMessage).where(ConversationMessage.created_at < message_cutoff)
        ) or 0

        escalations_to_delete = self.db.scalar(
            select(func.count())
            .select_from(EscalationTicket)
            .where(
                EscalationTicket.created_at < escalation_cutoff,
                EscalationTicket.status.in_(["resolved", "closed"]),
            )
        ) or 0

        deleted_messages = 0
        deleted_escalations = 0
        if not dry_run:
            deleted_messages = (
                self.db.execute(delete(ConversationMessage).where(ConversationMessage.created_at < message_cutoff))
                .rowcount
                or 0
            )
            deleted_escalations = (
                self.db.execute(
                    delete(EscalationTicket).where(
                        EscalationTicket.created_at < escalation_cutoff,
                        EscalationTicket.status.in_(["resolved", "closed"]),
                    )
                ).rowcount
                or 0
            )
            self.db.add(
                AuditLog(
                    actor=updated_by,
                    action="retention_cleanup",
                    payload_json={
                        "message_cutoff": message_cutoff.isoformat(),
                        "escalation_cutoff": escalation_cutoff.isoformat(),
                        "deleted_messages": deleted_messages,
                        "deleted_escalations": deleted_escalations,
                    },
                )
            )
            self.db.commit()

        return {
            "dry_run": dry_run,
            "message_cutoff": message_cutoff.isoformat(),
            "escalation_cutoff": escalation_cutoff.isoformat(),
            "messages_to_delete": int(messages_to_delete),
            "escalations_to_delete": int(escalations_to_delete),
            "deleted_messages": int(deleted_messages),
            "deleted_escalations": int(deleted_escalations),
        }
