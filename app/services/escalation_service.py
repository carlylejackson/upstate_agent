from sqlalchemy.orm import Session

from app.db.models import EscalationTicket
from app.integrations.email_client import EmailClient


class EscalationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.email = EmailClient()

    def create_ticket(
        self,
        session_id: str,
        channel: str,
        reason: str,
        conversation_excerpt: str,
        priority: str = "medium",
    ) -> EscalationTicket:
        ticket = EscalationTicket(
            session_id=session_id,
            channel=channel,
            reason=reason,
            conversation_excerpt=conversation_excerpt,
            priority=priority,
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)

        self.email.send(
            subject=f"[Escalation] {priority.upper()} - {reason}",
            body=(
                f"Ticket: {ticket.id}\n"
                f"Session: {session_id}\n"
                f"Channel: {channel}\n"
                f"Reason: {reason}\n\n"
                f"Excerpt:\n{conversation_excerpt}"
            ),
        )
        return ticket
