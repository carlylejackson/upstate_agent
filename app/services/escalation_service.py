from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import EscalationTicket
from app.integrations.email_client import EmailClient
from app.services.privacy_service import PrivacyService


class EscalationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.email = EmailClient()
        self.settings = get_settings()
        self.privacy = PrivacyService()

    def create_ticket(
        self,
        session_id: str,
        channel: str,
        reason: str,
        conversation_excerpt: str,
        priority: str = "medium",
    ) -> EscalationTicket:
        sanitized_excerpt = self.privacy.redact_text(conversation_excerpt or "")
        ticket = EscalationTicket(
            session_id=session_id,
            channel=channel,
            reason=reason,
            conversation_excerpt=sanitized_excerpt,
            priority=priority,
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)

        self.email.send(
            subject=f"[Escalation] {priority.upper()} - {reason}",
            body=self._build_email_body(
                ticket_id=ticket.id,
                session_id=session_id,
                channel=channel,
                reason=reason,
                conversation_excerpt=sanitized_excerpt,
                priority=priority,
            ),
        )
        return ticket

    def _build_email_body(
        self,
        ticket_id: str,
        session_id: str,
        channel: str,
        reason: str,
        conversation_excerpt: str,
        priority: str,
    ) -> str:
        base = [
            f"Ticket: {ticket_id}",
            f"Session: {session_id}",
            f"Channel: {channel}",
            f"Priority: {priority}",
            f"Reason: {reason}",
        ]

        # Minimize outbound email content by default in non-PHI phase.
        if not self.settings.escalation_email_include_excerpt:
            base.append("")
            base.append("Excerpt omitted by policy.")
            return "\n".join(base)

        redacted = self.privacy.redact_text(conversation_excerpt or "")
        excerpt = redacted[: max(self.settings.escalation_email_excerpt_max_chars, 1)]
        base.extend(["", "Excerpt (redacted):", excerpt])
        return "\n".join(base)
