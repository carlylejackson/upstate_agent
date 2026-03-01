import hmac

from fastapi import Header, HTTPException

from app.core.config import get_settings


async def verify_admin_key(x_admin_key: str = Header(default="")) -> None:
    settings = get_settings()
    if not any(hmac.compare_digest(x_admin_key, key) for key in settings.admin_api_keys_list):
        raise HTTPException(status_code=401, detail="Invalid admin API key")


async def verify_escalation_key(x_escalation_key: str = Header(default="")) -> None:
    settings = get_settings()
    if not hmac.compare_digest(x_escalation_key, settings.escalation_api_key):
        raise HTTPException(status_code=401, detail="Invalid escalation API key")
