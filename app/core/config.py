import json
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite:///./upstate_agent.db"

    openai_api_key: str | None = None
    default_model: str = "gpt-4.1-mini"
    fallback_model: str = "gpt-4.1"
    embedding_model: str = "text-embedding-3-small"

    admin_api_key: str = "change-me"
    phi_redaction_enabled: bool = True

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
