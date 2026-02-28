from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import ConversationMessage, ConversationSession, EscalationTicket, LeadCapture
from app.db.session import get_db
from app.schemas.common import HealthResponse

router = APIRouter(prefix="/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", app_env=settings.app_env)


@router.get("/metrics")
def metrics(db: Session = Depends(get_db)) -> dict:
    return {
        "sessions_total": db.scalar(select(func.count()).select_from(ConversationSession)) or 0,
        "messages_total": db.scalar(select(func.count()).select_from(ConversationMessage)) or 0,
        "escalations_open": db.scalar(
            select(func.count()).select_from(EscalationTicket).where(EscalationTicket.status == "open")
        )
        or 0,
        "lead_captures_total": db.scalar(select(func.count()).select_from(LeadCapture)) or 0,
    }
