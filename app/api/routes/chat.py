import hashlib
import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ConversationMessage, ConversationSession, LeadCapture
from app.db.session import get_db
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    CreateSessionRequest,
    SessionResponse,
)
from app.services.orchestration import AgentOrchestrator

router = APIRouter(prefix="/v1/chat", tags=["chat"])


def _hash_phone(phone: str) -> str:
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()


@router.post("/session", response_model=SessionResponse)
def create_session(payload: CreateSessionRequest, db: Session = Depends(get_db)) -> SessionResponse:
    phone_hash = _hash_phone(payload.phone_number) if payload.phone_number else None
    session = ConversationSession(
        channel=payload.channel,
        consent_to_contact=payload.consent_to_contact,
        phone_hash=phone_hash,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse(
        session_id=session.id,
        channel=session.channel,
        consent_to_contact=session.consent_to_contact,
        created_at=session.created_at,
    )


@router.post("/message", response_model=ChatMessageResponse)
def send_message(payload: ChatMessageRequest, db: Session = Depends(get_db)) -> ChatMessageResponse:
    session = db.scalar(select(ConversationSession).where(ConversationSession.id == payload.session_id))
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if payload.consent_to_contact is not None:
        session.consent_to_contact = payload.consent_to_contact
        db.commit()

    db.add(
        ConversationMessage(
            session_id=session.id,
            channel=payload.channel,
            role="user",
            text=payload.text,
        )
    )
    db.commit()

    result = AgentOrchestrator(db).run(session_id=session.id, channel=payload.channel, query=payload.text)

    db.add(
        ConversationMessage(
            session_id=session.id,
            channel=payload.channel,
            role="assistant",
            text=result.response_text,
            intent=result.intent,
            confidence=result.confidence,
            escalated=result.escalated,
            references_json=result.references,
        )
    )

    # Minimal lead capture: only after consent and appointment-related intent.
    if session.consent_to_contact and result.intent == "appointment_request":
        phone_match = re.search(r"(\+?1?[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}", payload.text)
        db.add(
            LeadCapture(
                session_id=session.id,
                phone=phone_match.group(0) if phone_match else None,
                reason=payload.text,
                consent=True,
                status="new",
            )
        )
    db.commit()

    return ChatMessageResponse(
        session_id=session.id,
        channel=payload.channel,
        intent=result.intent,
        confidence=result.confidence,
        escalated=result.escalated,
        response_text=result.response_text,
        references=result.references,
    )
