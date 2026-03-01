import re
from dataclasses import dataclass, field

from app.core.config import get_settings

EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(\+?1?[\s\-.]?)?\(?\d{3}\)?[\s\-.]?\d{3}[\s\-.]?\d{4}")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DOB_RE = re.compile(r"\b(?:dob|date of birth)\b[:\s\-]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", re.IGNORECASE)


@dataclass
class PrivacyScreenResult:
    restricted: bool
    reason: str | None
    redacted_text: str
    detected_signals: list[str] = field(default_factory=list)


class PrivacyService:
    EMERGENCY_TERMS = (
        "chest pain",
        "can't breathe",
        "cannot breathe",
        "stroke",
        "severe dizziness",
        "suicidal",
        "fainting",
    )
    MEDICAL_TERMS = (
        "tinnitus",
        "vertigo",
        "hearing loss",
        "ear pain",
        "dizzy",
        "dizziness",
        "diagnosed",
        "symptom",
        "infection",
        "bleeding",
        "migraine",
    )

    def __init__(self) -> None:
        self.settings = get_settings()

    def redact_text(self, text: str) -> str:
        redacted = text
        redacted = EMAIL_RE.sub("[REDACTED_EMAIL]", redacted)
        redacted = PHONE_RE.sub("[REDACTED_PHONE]", redacted)
        redacted = SSN_RE.sub("[REDACTED_SSN]", redacted)
        redacted = DOB_RE.sub("[REDACTED_DOB]", redacted)
        return redacted

    def non_phi_handoff_message(self, channel: str) -> str:
        if channel == "sms":
            return self.settings.non_phi_handoff_message_sms
        return self.settings.non_phi_handoff_message

    def screen_inbound(self, text: str, channel: str) -> PrivacyScreenResult:
        redacted_text = self.redact_text(text) if self.settings.redact_stored_messages else text
        mode = self.settings.compliance_mode.strip().lower()
        if mode != "non_phi":
            return PrivacyScreenResult(restricted=False, reason=None, redacted_text=redacted_text)

        lowered = text.lower()
        detected: list[str] = []
        if any(term in lowered for term in self.EMERGENCY_TERMS):
            detected.append("emergency_terms")
            return PrivacyScreenResult(
                restricted=True,
                reason="clinical_risk_or_emergency",
                redacted_text=redacted_text,
                detected_signals=detected,
            )

        if any(term in lowered for term in self.MEDICAL_TERMS):
            detected.append("medical_terms")
            return PrivacyScreenResult(
                restricted=True,
                reason="phase1_non_phi_restriction",
                redacted_text=redacted_text,
                detected_signals=detected,
            )

        return PrivacyScreenResult(
            restricted=False,
            reason=None,
            redacted_text=redacted_text,
            detected_signals=detected,
        )
