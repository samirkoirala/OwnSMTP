from unittest.mock import MagicMock, patch

import pytest

from email_gateway.config import Settings
from email_gateway.mailer import MailDeliveryError, SenderNotAllowedError, SMTPMailer
from email_gateway.schemas import EmailRequest


@patch("email_gateway.mailer.smtplib.SMTP")
def test_send_email_uses_starttls_and_auth(
    mock_smtp: MagicMock,
    settings: Settings,
    email_request: EmailRequest,
):
    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server
    server.has_extn.return_value = True
    server.send_message.return_value = {}

    SMTPMailer(settings).send(email_request)

    server.starttls.assert_called_once()
    server.login.assert_called_once_with("mailer@example.com", "secret")
    server.send_message.assert_called_once()


@patch("email_gateway.mailer.smtplib.SMTP")
def test_send_email_supports_unauthenticated_local_relay(
    mock_smtp: MagicMock,
    settings: Settings,
    email_request: EmailRequest,
):
    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server
    server.send_message.return_value = {}
    local_settings = settings.model_copy(
        update={
            "smtp_auth": False,
            "smtp_security": "none",
            "smtp_username": "",
            "smtp_password": "",
        }
    )

    SMTPMailer(local_settings).send(email_request)

    server.starttls.assert_not_called()
    server.login.assert_not_called()


@patch("email_gateway.mailer.smtplib.SMTP")
def test_starttls_is_not_silently_downgraded(
    mock_smtp: MagicMock,
    settings: Settings,
    email_request: EmailRequest,
):
    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server
    server.has_extn.return_value = False

    with pytest.raises(MailDeliveryError, match="STARTTLS"):
        SMTPMailer(settings).send(email_request)

    server.login.assert_not_called()
    server.send_message.assert_not_called()


@patch("email_gateway.mailer.smtplib.SMTP")
def test_refused_recipient_is_a_delivery_error(
    mock_smtp: MagicMock,
    settings: Settings,
    email_request: EmailRequest,
):
    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server
    server.has_extn.return_value = True
    server.send_message.return_value = {"person@example.com": (550, b"rejected")}

    with pytest.raises(MailDeliveryError, match="refused"):
        SMTPMailer(settings).send(email_request)


def test_html_message_has_plain_text_fallback(
    settings: Settings,
    email_request: EmailRequest,
):
    message = SMTPMailer(settings)._build_message(email_request)
    assert message.is_multipart()
    assert len(message.get_payload()) == 2
    assert message["Message-ID"]


@patch("email_gateway.mailer.smtplib.SMTP")
def test_allowed_visible_sender_keeps_configured_envelope_sender(
    mock_smtp: MagicMock,
    settings: Settings,
):
    server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = server
    server.has_extn.return_value = True
    server.send_message.return_value = {}
    request = EmailRequest(
        recipient_email=["person@example.com"],
        subject="Test",
        body="Hello",
        from_email="notifications@example.com",
        from_name="Notifications",
    )

    SMTPMailer(settings).send(request)

    message = server.send_message.call_args.args[0]
    assert message["From"] == "Notifications <notifications@example.com>"
    assert server.send_message.call_args.kwargs["from_addr"] == "mailer@example.com"


def test_sender_outside_allowlist_is_rejected(
    settings: Settings,
    email_request: EmailRequest,
):
    request = email_request.model_copy(update={"from_email": "attacker@outside.example"})

    with pytest.raises(SenderNotAllowedError, match="not allowed"):
        SMTPMailer(settings).send(request)
