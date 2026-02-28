import base64
import hashlib
import hmac
from urllib.parse import urlparse

from fastapi import HTTPException, Request

from app.core.config import get_settings


def _normalized_url(request: Request) -> str:
    # Twilio signs the full URL excluding default ports.
    url = str(request.url)
    parsed = urlparse(url)
    scheme = parsed.scheme
    host = parsed.hostname or ""
    port = parsed.port
    path = parsed.path or ""
    query = f"?{parsed.query}" if parsed.query else ""

    include_port = port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80))
    host_port = f"{host}:{port}" if include_port else host
    return f"{scheme}://{host_port}{path}{query}"


def compute_twilio_signature(url: str, params: dict[str, str], auth_token: str) -> str:
    payload = url + "".join(f"{k}{params[k]}" for k in sorted(params))
    digest = hmac.new(auth_token.encode("utf-8"), payload.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8")


def validate_twilio_request(request: Request, params: dict[str, str], signature: str | None) -> None:
    settings = get_settings()
    if not settings.twilio_validate_signatures:
        return

    if not settings.twilio_auth_token:
        raise HTTPException(status_code=500, detail="Twilio signature validation enabled without auth token")

    if not signature:
        raise HTTPException(status_code=401, detail="Missing Twilio signature")

    expected = compute_twilio_signature(_normalized_url(request), params, settings.twilio_auth_token)
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid Twilio signature")
