from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Base, BusinessPolicy
from app.db.session import get_engine

DEFAULT_POLICIES = {
    "business_hours": "Monday-Friday 9:00 AM-4:00 PM ET. Appointments available by request outside these hours.",
    "phone": "(864) 770-8822",
    "address": "25 Woods Lake Rd Suite 401, Greenville, SC 29607",
    "emergency_disclaimer": "I can't provide emergency medical advice. If this is urgent or severe, call 911 or seek immediate care.",
    "callback_sla": "Front desk follows up on callbacks during business hours.",
}


def init_db(session: Session) -> None:
    Base.metadata.create_all(bind=get_engine())
    for key, value in DEFAULT_POLICIES.items():
        existing = session.scalar(
            select(BusinessPolicy).where(
                BusinessPolicy.policy_key == key,
                BusinessPolicy.effective_to.is_(None),
            )
        )
        if existing:
            continue
        session.add(
            BusinessPolicy(
                policy_key=key,
                policy_value=value,
                effective_from=datetime.now(timezone.utc),
                updated_by="system",
            )
        )
    session.commit()
