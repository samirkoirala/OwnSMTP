import pytest
from pydantic import ValidationError

from email_gateway.config import Settings, get_settings


def test_authentication_requires_credentials():
    with pytest.raises(ValidationError):
        Settings(
            api_key="a" * 64,
            smtp_host="smtp.example.com",
            smtp_from_email="mailer@example.com",
            smtp_auth=True,
        )


def test_unauthenticated_relay_does_not_require_credentials():
    configured = Settings(
        api_key="a" * 64,
        smtp_host="smtp.example.com",
        smtp_from_email="mailer@example.com",
        smtp_auth=False,
        smtp_security="none",
    )
    assert configured.smtp_auth is False


def test_from_name_rejects_header_injection():
    with pytest.raises(ValidationError):
        Settings(
            api_key="a" * 64,
            smtp_host="smtp.example.com",
            smtp_from_email="mailer@example.com",
            smtp_auth=False,
            smtp_from_name="Sender\nBcc: attacker@example.com",
        )


def test_settings_load_from_environment(monkeypatch):
    monkeypatch.setenv("API_KEY", "a" * 64)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "mailer@example.com")
    monkeypatch.setenv("SMTP_AUTH", "off")
    monkeypatch.setenv("SMTP_SECURITY", "none")
    monkeypatch.delenv("ALLOWED_FROM_DOMAINS", raising=False)
    get_settings.cache_clear()

    configured = get_settings()

    assert configured.smtp_host == "smtp.example.com"
    assert configured.smtp_auth is False
    assert configured.allowed_from_domains == {"example.com"}


def test_settings_reject_invalid_environment_boolean(monkeypatch):
    monkeypatch.setenv("API_KEY", "a" * 64)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "mailer@example.com")
    monkeypatch.setenv("SMTP_AUTH", "sometimes")

    with pytest.raises(ValueError, match="must be true or false"):
        Settings.from_environment()


def test_settings_report_missing_environment(monkeypatch):
    for name in ("API_KEY", "SMTP_HOST", "SMTP_FROM_EMAIL"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValueError, match="API_KEY, SMTP_HOST, SMTP_FROM_EMAIL"):
        Settings.from_environment()


def test_sender_domain_allowlist_is_case_insensitive():
    configured = Settings(
        api_key="a" * 64,
        smtp_host="smtp.example.com",
        smtp_from_email="no-reply@techyatralabs.com",
        smtp_auth=False,
        allowed_from_domains={"TechYatraLabs.COM"},
    )

    assert configured.allows_sender("anything@techyatralabs.com")
    assert not configured.allows_sender("anything@example.com")
