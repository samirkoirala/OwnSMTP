"""Application configuration loaded from environment variables."""

import os
from functools import lru_cache
from typing import Literal, cast

from dotenv import load_dotenv
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

load_dotenv()


def _environment_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


class Settings(BaseModel):
    """Validated runtime settings."""

    api_key: str = Field(min_length=32)
    smtp_host: str = Field(min_length=1)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_auth: bool = True
    smtp_from_email: EmailStr
    smtp_from_name: str = Field(default="Notification Service", min_length=1, max_length=255)
    allowed_from_domains: set[str] = Field(default_factory=set)
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    smtp_timeout_seconds: float = Field(default=15.0, gt=0, le=120)

    @field_validator("smtp_from_name")
    @classmethod
    def reject_header_injection(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("smtp_from_name must not contain newlines")
        return value

    @model_validator(mode="after")
    def validate_authentication(self) -> "Settings":
        if self.smtp_auth and (not self.smtp_username or not self.smtp_password):
            raise ValueError("SMTP_USERNAME and SMTP_PASSWORD are required when SMTP_AUTH=true")
        if not self.allowed_from_domains:
            self.allowed_from_domains = {str(self.smtp_from_email).rsplit("@", 1)[1].lower()}
        return self

    @field_validator("allowed_from_domains")
    @classmethod
    def normalize_allowed_domains(cls, value: set[str]) -> set[str]:
        normalized = {domain.strip().lower().rstrip(".") for domain in value if domain.strip()}
        if any("@" in domain or "." not in domain for domain in normalized):
            raise ValueError("ALLOWED_FROM_DOMAINS must contain domain names")
        return normalized

    def allows_sender(self, email: EmailStr) -> bool:
        return str(email).rsplit("@", 1)[1].lower() in self.allowed_from_domains

    @classmethod
    def from_environment(cls) -> "Settings":
        required = ("API_KEY", "SMTP_HOST", "SMTP_FROM_EMAIL")
        missing = [name for name in required if not os.getenv(name, "").strip()]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return cls(
            api_key=os.environ["API_KEY"],
            smtp_host=os.environ["SMTP_HOST"],
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_auth=_environment_bool("SMTP_AUTH", True),
            smtp_from_email=os.environ["SMTP_FROM_EMAIL"],
            smtp_from_name=os.getenv("SMTP_FROM_NAME", "Notification Service"),
            allowed_from_domains=set(os.getenv("ALLOWED_FROM_DOMAINS", "").split(",")),
            smtp_security=cast(
                Literal["starttls", "ssl", "none"],
                os.getenv("SMTP_SECURITY", "starttls").lower(),
            ),
            smtp_timeout_seconds=float(os.getenv("SMTP_TIMEOUT_SECONDS", "15")),
        )


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
