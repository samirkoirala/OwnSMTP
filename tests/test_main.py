from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from pydantic import ValidationError

from main import EmailRequest, Settings, require_api_key, send_email


def settings(**overrides) -> Settings:
    values = {
        "api_key": "a" * 64,
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_username": "mailer@example.com",
        "smtp_password": "secret",
        "smtp_from_email": "mailer@example.com",
        "smtp_from_name": "Test App",
        "smtp_security": "starttls",
        "smtp_auth": True,
    }
    values.update(overrides)
    return Settings(**values)


def request() -> EmailRequest:
    return EmailRequest(
        recipient_email=["person@example.com"],
        subject="Test",
        body="<strong>Hello</strong>",
    )


def test_api_key_is_required():
    with pytest.raises(HTTPException) as error:
        require_api_key(None, settings())
    assert error.value.status_code == 401


def test_valid_api_key_is_accepted():
    require_api_key("a" * 64, settings())


def test_subject_rejects_header_injection():
    with pytest.raises(ValidationError):
        EmailRequest(
            recipient_email=["person@example.com"],
            subject="Valid subject\nBcc: attacker@example.com",
            body="Hello",
        )


@patch("main.smtplib.SMTP")
def test_send_email_uses_starttls_and_auth(mock_smtp):
    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server
    server.sendmail.return_value = {}

    response = send_email(request(), settings())

    assert response.status == "success"
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("mailer@example.com", "secret")
    server.sendmail.assert_called_once()


@patch("main.smtplib.SMTP")
def test_send_email_supports_unauthenticated_local_relay(mock_smtp):
    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server
    server.sendmail.return_value = {}

    send_email(
        request(),
        settings(smtp_auth=False, smtp_security="none", smtp_username="", smtp_password=""),
    )

    server.starttls.assert_not_called()
    server.login.assert_not_called()
    server.sendmail.assert_called_once()
