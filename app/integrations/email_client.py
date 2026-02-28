import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def send(self, subject: str, body: str, to_address: str | None = None) -> None:
        if not self.settings.smtp_host:
            logger.info("SMTP not configured, skipping email", extra={"subject": subject})
            return

        recipient = to_address or self.settings.escalation_email_to
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self.settings.escalation_email_from
        message["To"] = recipient
        message.set_content(body)

        try:
            with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
                if self.settings.smtp_use_tls:
                    server.starttls()
                if self.settings.smtp_username and self.settings.smtp_password:
                    server.login(self.settings.smtp_username, self.settings.smtp_password)
                server.send_message(message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("SMTP send failed; escalation persisted without email notification: %s", exc)
