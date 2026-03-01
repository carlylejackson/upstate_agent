import hashlib

from fastapi import APIRouter, Depends, Form, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConversationMessage, ConversationSession
from app.db.session import get_db
from app.integrations.twilio_security import validate_twilio_request
from app.integrations.twilio_xml import twiml_message
from app.services.orchestration import AgentOrchestrator
from app.services.privacy_service import PrivacyService

router = APIRouter(prefix="/v1/sms", tags=["sms"])


def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


@router.post("/webhook/twilio")
def twilio_sms_webhook(
    request: Request,
    db: Session = Depends(get_db),
    from_number: str = Form(alias="From"),
    body: str = Form(alias="Body"),
    twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
) -> Response:
    validate_twilio_request(
        request=request,
        params={"From": from_number, "Body": body},
        signature=twilio_signature,
    )

    phone_hash = _hash_phone(from_number)
    privacy_service = PrivacyService()
    screened = privacy_service.screen_inbound(body, "sms")
    session = db.scalar(select(ConversationSession).where(ConversationSession.phone_hash == phone_hash))
    if not session:
        session = ConversationSession(channel="sms", phone_hash=phone_hash)
        db.add(session)
        db.commit()
        db.refresh(session)

    db.add(
        ConversationMessage(session_id=session.id, channel="sms", role="user", text=screened.redacted_text)
    )
    db.commit()

    result = AgentOrchestrator(db).run(session_id=session.id, channel="sms", query=body)

    db.add(
        ConversationMessage(
            session_id=session.id,
            channel="sms",
            role="assistant",
            text=result.response_text,
            intent=result.intent,
            confidence=result.confidence,
            escalated=result.escalated,
            references_json=result.references,
        )
    )
    db.commit()

    return Response(content=twiml_message(result.response_text), media_type="application/xml")
