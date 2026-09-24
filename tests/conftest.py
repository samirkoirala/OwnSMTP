import pytest

from email_gateway.config import Settings
from email_gateway.schemas import EmailRequest


@pytest.fixture
def settings() -> Settings:
    return Settings(
        api_key="a" * 64,
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="mailer@example.com",
        smtp_password="secret",
        smtp_from_email="mailer@example.com",
        smtp_from_name="Test App",
        smtp_security="starttls",
        smtp_auth=True,
    )


@pytest.fixture
def email_request() -> EmailRequest:
    return EmailRequest(
        recipient_email=["person@example.com"],
        subject="Test",
        body="<strong>Hello</strong>",
    )
