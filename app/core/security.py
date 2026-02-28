from fastapi import Header, HTTPException

from app.core.config import get_settings


async def verify_admin_key(x_admin_key: str = Header(default="")) -> None:
    settings = get_settings()
    if x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
