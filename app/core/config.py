import json
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./upstate_agent.db"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000,http://127.0.0.1:8000"

    openai_api_key: str | None = None
    default_model: str = "gpt-4.1-mini"
    fallback_model: str = "gpt-4.1"
    embedding_model: str = "text-embedding-3-small"

    admin_api_key: str = "change-me"
    phi_redaction_enabled: bool = True
    compliance_mode: str = "non_phi"
    redact_stored_messages: bool = True
    non_phi_handoff_message: str = (
        "Thanks for reaching out. For privacy and safety, I can't handle clinical or health-specific "
        "details in this chat right now. I can connect you with our team for direct follow-up."
    )
    non_phi_handoff_message_sms: str = (
        "For privacy, please do not share health details by text. "
        "Reply with your callback number and preferred time, and our team will follow up."
    )
    retention_days_messages: int = 30
    retention_days_escalations: int = 90

    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_phone_number: str | None = None
    twilio_validate_signatures: bool = False

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    escalation_email_to: str = "frontdesk@example.com"
    escalation_email_from: str = "bot@example.com"

    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 300
    rate_limit_exempt_paths: str = "/,/v1/health,/v1/metrics,/docs,/openapi.json,/chat-test"

    kb_source_urls: str = (
        "https://www.upstatehearingandbalance.com/,"
        "https://www.upstatehearingandbalance.com/contact-us,"
        "https://www.upstatehearingandbalance.com/services,"
        "https://www.upstatehearingandbalance.com/insurance-financing"
    )
    manual_policy_approval: bool = True

    timezone: str = "America/New_York"

    @field_validator("kb_source_urls", mode="before")
    @classmethod
    def normalize_kb_source_urls(cls, value: str | list[str]) -> str:
        if isinstance(value, list):
            return ",".join(item.strip() for item in value if item and item.strip())
        if not isinstance(value, str):
            return ""
        raw = value.strip()
        if not raw:
            return ""
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return ",".join(str(item).strip() for item in parsed if str(item).strip())
            except json.JSONDecodeError:
                pass
        return raw

    @property
    def kb_source_urls_list(self) -> list[str]:
        return [item.strip() for item in self.kb_source_urls.split(",") if item.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        if self.app_env == "production":
            return [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        dev_defaults = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"]
        custom = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        return sorted(set(dev_defaults + custom))

    @property
    def rate_limit_exempt_paths_list(self) -> list[str]:
        return [item.strip() for item in self.rate_limit_exempt_paths.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
