"""HTTP routes for the relay API."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from .config import Settings, get_settings
from .mailer import MailDeliveryError, SenderNotAllowedError, SMTPMailer
from .schemas import EmailRequest, EmailResponse, HealthResponse
from .security import require_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/healthz", response_model=HealthResponse, include_in_schema=False)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/readyz", response_model=HealthResponse, include_in_schema=False)
def readiness() -> HealthResponse:
    try:
        get_settings()
    except (ValueError, TypeError):
        raise HTTPException(status_code=503, detail="Service is not configured") from None
    return HealthResponse(status="ready")


def deliver_email(
    email_request: EmailRequest,
    settings: Settings = Depends(get_settings),
) -> EmailResponse:
    try:
        SMTPMailer(settings).send(email_request)
    except SenderNotAllowedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from None
    except MailDeliveryError:
        logger.exception("SMTP delivery failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Email delivery failed",
        ) from None
    return EmailResponse()


for path, description in (
    ("/send-email", None),
    ("/v1/emails", "Versioned alias for POST /send-email."),
):
    router.add_api_route(
        path,
        deliver_email,
        methods=["POST"],
        response_model=EmailResponse,
        dependencies=[Depends(require_api_key)],
        tags=["email"],
        summary="Send an email",
        description=description,
    )
