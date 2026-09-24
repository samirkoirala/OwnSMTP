"""HTTP request and response models."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmailRequest(BaseModel):
    recipient_email: list[EmailStr] = Field(min_length=1, max_length=50)
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=1_000_000)
    body_type: Literal["html", "plain"] = "html"
    from_email: EmailStr | None = None
    from_name: str | None = Field(default=None, min_length=1, max_length=255)
    reply_to: EmailStr | None = None

    @field_validator("subject")
    @classmethod
    def reject_header_newlines(cls, value: str) -> str:
        if "\r" in value or "\n" in value:
            raise ValueError("subject must not contain newlines")
        return value

    @field_validator("from_name")
    @classmethod
    def reject_sender_name_header_newlines(cls, value: str | None) -> str | None:
        if value is not None and ("\r" in value or "\n" in value):
            raise ValueError("from_name must not contain newlines")
        return value

    @field_validator("recipient_email")
    @classmethod
    def reject_duplicate_recipients(cls, value: list[EmailStr]) -> list[EmailStr]:
        normalized = [str(address).lower() for address in value]
        if len(normalized) != len(set(normalized)):
            raise ValueError("recipient_email must not contain duplicates")
        return value


class EmailResponse(BaseModel):
    status: Literal["success"] = "success"
    message: str = "Email accepted by SMTP server"


class HealthResponse(BaseModel):
    status: Literal["ok", "ready"]
