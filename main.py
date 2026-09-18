import logging
import os
import secrets
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, field_validator

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("email_gateway")

app = FastAPI(
    title="Internal Email Gateway",
    description="Authenticated internal HTTP gateway for sending email through one SMTP relay.",
    version="1.0.0",
    docs_url=None if os.getenv("DISABLE_DOCS", "false").lower() == "true" else "/docs",
    redoc_url=None,
)


class Settings(BaseModel):
    api_key: str = Field(min_length=32)
    smtp_host: str
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_auth: bool = True
    smtp_from_email: EmailStr
    smtp_from_name: str = "Notification Service"
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    smtp_timeout_seconds: float = Field(default=15.0, gt=0, le=120)


@lru_cache
def get_settings() -> Settings:
    required = ("API_KEY", "SMTP_HOST", "SMTP_FROM_EMAIL")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    smtp_auth = os.getenv("SMTP_AUTH", "true").lower() == "true"
    if smtp_auth and (not os.getenv("SMTP_USERNAME") or not os.getenv("SMTP_PASSWORD")):
        raise RuntimeError("SMTP_USERNAME and SMTP_PASSWORD are required when SMTP_AUTH=true")

    return Settings(
        api_key=os.environ["API_KEY"],
        smtp_host=os.environ["SMTP_HOST"],
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_auth=smtp_auth,
        smtp_from_email=os.environ["SMTP_FROM_EMAIL"],
        smtp_from_name=os.getenv("SMTP_FROM_NAME", "Notification Service"),
        smtp_security=os.getenv("SMTP_SECURITY", "starttls").lower(),
        smtp_timeout_seconds=float(os.getenv("SMTP_TIMEOUT_SECONDS", "15")),
    )


class EmailRequest(BaseModel):
    recipient_email: list[EmailStr] = Field(min_length=1, max_length=50)
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=1_000_000)
    body_type: Literal["html", "plain"] = "html"
    reply_to: EmailStr | None = None

    @field_validator("subject")
    @classmethod
    def reject_header_newlines(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("subject must not contain newlines")
        return value


class EmailResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str = "Email accepted by SMTP server"


def require_api_key(
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> None:
    if x_api_key is None or not secrets.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


@app.get("/healthz", include_in_schema=False)
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
def readiness() -> dict[str, str]:
    try:
        get_settings()
    except (RuntimeError, ValueError):
        raise HTTPException(status_code=503, detail="Service is not configured") from None
    return {"status": "ready"}


@app.post(
    "/send-email",
    response_model=EmailResponse,
    dependencies=[Depends(require_api_key)],
)
def send_email(email_request: EmailRequest, settings: Settings = Depends(get_settings)) -> EmailResponse:
    message = MIMEMultipart("alternative")
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = ", ".join(str(address) for address in email_request.recipient_email)
    message["Subject"] = email_request.subject
    if email_request.reply_to:
        message["Reply-To"] = str(email_request.reply_to)
    message.attach(MIMEText(email_request.body, email_request.body_type, "utf-8"))

    recipients = [str(address) for address in email_request.recipient_email]
    tls_context = ssl.create_default_context()

    try:
        if settings.smtp_security == "ssl":
            smtp_client = smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
                context=tls_context,
            )
        else:
            smtp_client = smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=settings.smtp_timeout_seconds,
            )

        with smtp_client as server:
            if settings.smtp_security == "starttls":
                server.starttls(context=tls_context)
            if settings.smtp_auth:
                server.login(settings.smtp_username, settings.smtp_password)
            refused = server.sendmail(str(settings.smtp_from_email), recipients, message.as_string())

        if refused:
            logger.warning("SMTP server refused %d recipient(s)", len(refused))
            raise HTTPException(status_code=502, detail="SMTP server refused one or more recipients")

        logger.info("Email delivered to SMTP server for %d recipient(s)", len(recipients))
        return EmailResponse()
    except HTTPException:
        raise
    except (smtplib.SMTPException, OSError):
        logger.exception("SMTP delivery failed")
        raise HTTPException(status_code=502, detail="Email delivery failed") from None
