import pytest
from pydantic import ValidationError

from email_gateway.schemas import EmailRequest


def test_subject_rejects_header_injection():
    with pytest.raises(ValidationError):
        EmailRequest(
            recipient_email=["person@example.com"],
            subject="Valid subject\nBcc: attacker@example.com",
            body="Hello",
        )


def test_duplicate_recipients_are_rejected():
    with pytest.raises(ValidationError):
        EmailRequest(
            recipient_email=["Person@example.com", "person@example.com"],
            subject="Test",
            body="Hello",
        )


def test_sender_name_rejects_header_injection():
    with pytest.raises(ValidationError):
        EmailRequest(
            recipient_email=["person@example.com"],
            subject="Test",
            body="Hello",
            from_name="Trusted sender\nBcc: attacker@example.com",
        )
