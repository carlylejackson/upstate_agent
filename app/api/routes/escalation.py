from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.escalation import EscalationRequest, EscalationResponse
from app.services.escalation_service import EscalationService

router = APIRouter(prefix="/v1", tags=["escalation"])


@router.post("/escalations", response_model=EscalationResponse)
def create_escalation(payload: EscalationRequest, db: Session = Depends(get_db)) -> EscalationResponse:
    ticket = EscalationService(db).create_ticket(
        session_id=payload.session_id,
        channel=payload.channel,
        reason=payload.reason,
        conversation_excerpt=payload.conversation_excerpt,
        priority=payload.priority,
    )
    return EscalationResponse(ticket_id=ticket.id, status=ticket.status)
