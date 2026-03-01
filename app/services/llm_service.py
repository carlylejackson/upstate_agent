import json
import logging
import re

from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)

INTENTS = [
    "hours_location_contact",
    "services_info",
    "insurance_financing",
    "appointment_request",
    "device_support_general",
    "billing_admin",
    "clinical_risk_or_emergency",
    "other_unknown",
]


class LLMService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key) if self.settings.openai_api_key else None

    def _heuristic_intent(self, text: str) -> tuple[str, float]:
        q = text.lower()
        if any(k in q for k in ["chest pain", "stroke", "can't breathe", "faint", "severe dizziness"]):
            return "clinical_risk_or_emergency", 0.98
        if any(k in q for k in ["hours", "open", "closed", "address", "location", "phone"]):
            return "hours_location_contact", 0.95
        if any(k in q for k in ["insurance", "medicare", "financing", "payment plan"]):
            return "insurance_financing", 0.9
        if any(k in q for k in ["appointment", "schedule", "book", "callback"]):
            return "appointment_request", 0.9
        if any(k in q for k in ["hearing aid", "device", "battery", "pair", "bluetooth"]):
            return "device_support_general", 0.85
        if any(k in q for k in ["billing", "invoice", "receipt", "charge"]):
            return "billing_admin", 0.85
        if any(k in q for k in ["service", "offer", "treatment", "test"]):
            return "services_info", 0.8
        return "other_unknown", 0.55

    def classify_intent(self, text: str) -> tuple[str, float]:
        heuristic_intent, heuristic_conf = self._heuristic_intent(text)
        if not self.client:
            return heuristic_intent, heuristic_conf

        prompt = (
            "Classify user support intent into exactly one label from this list: "
            f"{', '.join(INTENTS)}. Return JSON with keys intent and confidence. "
            f"Text: {text}"
        )
        try:
            result = self.client.responses.create(model=self.settings.default_model, input=prompt)
            output_text = result.output_text.strip()
            payload = json.loads(output_text)
            intent = payload.get("intent", heuristic_intent)
            confidence = float(payload.get("confidence", heuristic_conf))
            if intent not in INTENTS:
                return heuristic_intent, heuristic_conf
            return intent, max(0.0, min(confidence, 1.0))
        except Exception as exc:  # noqa: BLE001
            logger.warning("intent classification fallback: %s", exc)
            return heuristic_intent, heuristic_conf

    def generate_response(
        self,
        query: str,
        intent: str,
        references: list[dict],
        policies: dict[str, str],
        channel: str = "web",
    ) -> str:
        if intent == "appointment_request":
            if channel == "sms":
                return (
                    "I can help with that. Reply with your first name, best callback number, and preferred "
                    "appointment time. By replying with contact details, you consent to staff follow-up."
                )
            return (
                "I can help with that. Please share your name, best callback number, and preferred appointment time. "
                "By sharing contact details, you consent to front desk follow-up."
            )

        if intent == "clinical_risk_or_emergency":
            return policies.get(
                "emergency_disclaimer",
                "If this is urgent or severe, call 911 or seek immediate care.",
            )

        if not self.client:
            return self._fallback_response(query, intent, references, policies)

        refs_text = "\n".join(
            f"- {ref['title']} ({ref['source_url']}): {ref['snippet']}" for ref in references
        )
        system_prompt = (
            "You are an operational customer support assistant for a hearing and balance clinic. "
            "Never diagnose. Be concise. Use provided policy and references only. "
            "If references are insufficient, ask for clarification or offer escalation."
        )
        user_prompt = (
            f"Intent: {intent}\n"
            f"Policies: {json.dumps(policies)}\n"
            f"References:\n{refs_text or '- none'}\n"
            f"User query: {query}"
        )
        try:
            result = self.client.responses.create(
                model=self.settings.default_model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = result.output_text.strip()
            return text or self._fallback_response(query, intent, references, policies)
        except Exception as exc:  # noqa: BLE001
            logger.warning("response generation fallback: %s", exc)
            return self._fallback_response(query, intent, references, policies)

    def embed_text(self, text: str) -> list[float] | None:
        if not self.client:
            return None
        try:
            response = self.client.embeddings.create(model=self.settings.embedding_model, input=text)
            return response.data[0].embedding
        except Exception as exc:  # noqa: BLE001
            logger.warning("embedding fallback: %s", exc)
            return None

    def _fallback_response(
        self,
        query: str,
        intent: str,
        references: list[dict],
        policies: dict[str, str],
    ) -> str:
        if intent == "insurance_financing":
            return (
                "We can help with insurance and financing questions. "
                "Please share your insurance provider and we can route this to staff for confirmation."
            )
        if intent == "services_info":
            return "We offer hearing and balance-related services. Tell me what you need help with and I can guide you."
        if intent == "device_support_general":
            return (
                "I can help with general hearing-device support. "
                "Please describe the device issue and I can suggest next steps or escalate to staff."
            )
        if intent == "billing_admin":
            return (
                "For billing questions, please share your order or invoice details if available. "
                "I can route this to our team for follow-up."
            )
        if references:
            return f"Based on our available information: {references[0]['snippet']}"
        if re.search(r"hours|open|closed", query.lower()):
            return f"Our business hours are {policies.get('business_hours', 'Monday-Friday 9:00 AM-4:00 PM ET.')}"
        return (
            "I may need a team member to confirm that accurately. "
            "If you want, I can escalate this and collect callback details."
        )
