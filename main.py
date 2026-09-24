"""Compatibility entrypoint for existing deployments and imports."""

from email_gateway.api import deliver_email as send_email
from email_gateway.app import app, create_app
from email_gateway.config import Settings, get_settings
from email_gateway.schemas import EmailRequest, EmailResponse
from email_gateway.security import require_api_key

__all__ = [
    "EmailRequest",
    "EmailResponse",
    "Settings",
    "app",
    "create_app",
    "get_settings",
    "require_api_key",
    "send_email",
]
