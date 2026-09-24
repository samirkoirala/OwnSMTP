"""SMTP message construction and delivery."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from .config import Settings
from .schemas import EmailRequest

logger = logging.getLogger(__name__)


class MailDeliveryError(Exception):
    """Raised when an SMTP server does not accept a complete message."""


class SenderNotAllowedError(Exception):
    """Raised when a request uses a sender outside the configured domains."""


class SMTPMailer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, request: EmailRequest) -> None:
        if request.from_email and not self.settings.allows_sender(request.from_email):
            raise SenderNotAllowedError("Sender domain is not allowed")
        message = self._build_message(request)
        recipients = [str(address) for address in request.recipient_email]

        try:
            with self._connect() as server:
                server.ehlo()
                if self.settings.smtp_security == "starttls":
                    if not server.has_extn("starttls"):
                        raise MailDeliveryError("SMTP server does not support STARTTLS")
                    server.starttls(context=ssl.create_default_context())
                    server.ehlo()
                if self.settings.smtp_auth:
                    server.login(self.settings.smtp_username, self.settings.smtp_password)
                refused = server.send_message(
                    message,
                    from_addr=str(self.settings.smtp_from_email),
                    to_addrs=recipients,
                )
        except MailDeliveryError:
            raise
        except (smtplib.SMTPException, OSError) as exc:
            raise MailDeliveryError("SMTP delivery failed") from exc

        if refused:
            logger.warning("SMTP server refused %d recipient(s)", len(refused))
            raise MailDeliveryError("SMTP server refused one or more recipients")

        logger.info("Email accepted by SMTP server for %d recipient(s)", len(recipients))

    def _connect(self) -> smtplib.SMTP:
        if self.settings.smtp_security == "ssl":
            return smtplib.SMTP_SSL(
                host=self.settings.smtp_host,
                port=self.settings.smtp_port,
                timeout=self.settings.smtp_timeout_seconds,
                context=ssl.create_default_context(),
            )
        return smtplib.SMTP(
            host=self.settings.smtp_host,
            port=self.settings.smtp_port,
            timeout=self.settings.smtp_timeout_seconds,
        )

    def _build_message(self, request: EmailRequest) -> EmailMessage:
        visible_email = request.from_email or self.settings.smtp_from_email
        visible_name = request.from_name or self.settings.smtp_from_name
        message = EmailMessage()
        message["From"] = formataddr((visible_name, str(visible_email)))
        message["To"] = ", ".join(str(address) for address in request.recipient_email)
        message["Subject"] = request.subject
        domain = str(self.settings.smtp_from_email).split("@", 1)[1]
        message["Message-ID"] = make_msgid(domain=domain)
        if request.reply_to:
            message["Reply-To"] = str(request.reply_to)

        if request.body_type == "html":
            message.set_content("This message contains HTML. View it in an HTML-capable client.")
            message.add_alternative(request.body, subtype="html")
        else:
            message.set_content(request.body)
        return message
