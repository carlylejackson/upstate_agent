from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import EscalationTicket, LeadCapture
from app.db.session import get_session_factory
from app.integrations.email_client import EmailClient


def run_daily_digest() -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=1)
    session = get_session_factory()()
    email = EmailClient()

    try:
        escalations = session.scalars(
            select(EscalationTicket).where(
                EscalationTicket.created_at >= since,
                EscalationTicket.status == "open",
            )
        ).all()
        leads = session.scalars(select(LeadCapture).where(LeadCapture.created_at >= since)).all()

        body = [
            f"Daily digest for {now.date()}",
            "",
            f"Open escalations: {len(escalations)}",
            f"New lead captures: {len(leads)}",
            "",
        ]
        for ticket in escalations[:20]:
            body.append(f"- [{ticket.priority}] {ticket.reason} | session={ticket.session_id}")

        email.send(subject="Upstate Agent Daily Digest", body="\n".join(body))
        return {"escalations": len(escalations), "leads": len(leads)}
    finally:
        session.close()


if __name__ == "__main__":
    print(run_daily_digest())
