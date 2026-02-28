import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import BusinessPolicy


class PolicyService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def get_active_policies(self) -> dict[str, str]:
        rows = self.db.scalars(
            select(BusinessPolicy).where(BusinessPolicy.effective_to.is_(None))
        ).all()
        return {row.policy_key: row.policy_value for row in rows}

    def update_policy(self, key: str, value: str, updated_by: str) -> None:
        active = self.db.scalars(
            select(BusinessPolicy).where(
                BusinessPolicy.policy_key == key,
                BusinessPolicy.effective_to.is_(None),
            )
        ).all()
        now = datetime.now(timezone.utc)
        for row in active:
            row.effective_to = now
        self.db.add(BusinessPolicy(policy_key=key, policy_value=value, updated_by=updated_by))
        self.db.commit()

    def deterministic_response(self, query: str, policies: dict[str, str]) -> str | None:
        q = query.lower().strip()

        if re.search(r"(business\s*hours|hours|open|closed)", q):
            return (
                f"Our business hours are {policies.get('business_hours', '')} "
                "If you prefer, I can collect your details for a callback."
            ).strip()

        if re.search(r"(phone|call|number|contact)", q):
            return f"You can reach us at {policies.get('phone', '')}."

        if re.search(r"(address|location|where are you|directions)", q):
            return f"Our office is located at {policies.get('address', '')}."

        return None

    def is_open_now(self, policies: dict[str, str]) -> bool:
        # Grounded default schedule from policy assumptions: Mon-Fri 9-4 ET.
        tz = ZoneInfo(self.settings.timezone)
        now = datetime.now(tz)
        if now.weekday() >= 5:
            return False
        return 9 <= now.hour < 16
