import os


def _reset_settings():
    from app.core.config import get_settings

    get_settings.cache_clear()


def test_redact_text_masks_common_identifiers():
    os.environ["COMPLIANCE_MODE"] = "non_phi"
    _reset_settings()

    from app.services.privacy_service import PrivacyService

    service = PrivacyService()
    text = "Email me at user@example.com, call 864-770-8822, ssn 123-45-6789"
    redacted = service.redact_text(text)

    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_SSN]" in redacted


def test_screen_inbound_restricts_medical_content_in_non_phi_mode():
    os.environ["COMPLIANCE_MODE"] = "non_phi"
    _reset_settings()

    from app.services.privacy_service import PrivacyService

    service = PrivacyService()
    result = service.screen_inbound("I have tinnitus and hearing loss", channel="web")

    assert result.restricted is True
    assert result.reason == "phase1_non_phi_restriction"
    assert "medical_terms" in result.detected_signals


def test_non_phi_handoff_message_uses_sms_variant():
    os.environ["COMPLIANCE_MODE"] = "non_phi"
    _reset_settings()

    from app.services.privacy_service import PrivacyService

    service = PrivacyService()
    sms_msg = service.non_phi_handoff_message("sms")
    web_msg = service.non_phi_handoff_message("web")

    assert "text" in sms_msg.lower()
    assert sms_msg != web_msg
