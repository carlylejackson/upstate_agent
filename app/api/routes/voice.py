from fastapi import APIRouter, Depends, Form, Header, Request, Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.integrations.twilio_security import validate_twilio_request
from app.integrations.twilio_xml import twiml_say_and_hangup
from app.services.policy_service import PolicyService

router = APIRouter(prefix="/v1/voice", tags=["voice"])


@router.post("/webhook/twilio")
def twilio_voice_webhook(
    request: Request,
    db: Session = Depends(get_db),
    from_number: str = Form(default="", alias="From"),
    call_sid: str = Form(default="", alias="CallSid"),
    twilio_signature: str | None = Header(default=None, alias="X-Twilio-Signature"),
) -> Response:
    validate_twilio_request(
        request=request,
        params={"From": from_number, "CallSid": call_sid},
        signature=twilio_signature,
    )

    policies = PolicyService(db).get_active_policies()
    is_open = PolicyService(db).is_open_now(policies)
    if is_open:
        text = (
            f"Thanks for calling Upstate Hearing and Balance. "
            f"Please call our front desk at {policies.get('phone', '(864) 770-8822')} for immediate assistance."
        )
    else:
        text = (
            "We are currently outside business hours. "
            "Please leave a detailed voicemail, or use our website chat to request a callback."
        )

    return Response(content=twiml_say_and_hangup(text), media_type="application/xml")
