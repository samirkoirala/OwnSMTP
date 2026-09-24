"""Check SMTP connectivity and authentication, optionally sending one test email."""

import argparse
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required setting: {name}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify SMTP connection, TLS, and authentication without sending by default."
    )
    parser.add_argument("--env-file", default=".env", help="Environment file (default: .env)")
    parser.add_argument("--send-to", help="Send one real test email to this address")
    parser.add_argument(
        "--from-email",
        help="Override the visible From header; SMTP_FROM_EMAIL remains the envelope sender",
    )
    parser.add_argument("--subject", default="SMTP gateway test", help="Test email subject")
    parser.add_argument(
        "--body",
        default="SMTP connectivity, TLS, authentication, and delivery submission worked.",
        help="Plain-text test email body",
    )
    args = parser.parse_args()

    load_env(Path(args.env_file))
    host = required("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    security = os.getenv("SMTP_SECURITY", "starttls").lower()
    use_auth = os.getenv("SMTP_AUTH", "true").lower() == "true"
    timeout = float(os.getenv("SMTP_TIMEOUT_SECONDS", "15"))

    if security not in {"starttls", "ssl", "none"}:
        raise SystemExit("SMTP_SECURITY must be starttls, ssl, or none")

    context = ssl.create_default_context()
    smtp_class = smtplib.SMTP_SSL if security == "ssl" else smtplib.SMTP
    kwargs = {"host": host, "port": port, "timeout": timeout}
    if security == "ssl":
        kwargs["context"] = context

    print(f"Connecting to {host}:{port} ({security}) ...")
    try:
        with smtp_class(**kwargs) as server:
            server.ehlo()
            print("SMTP connection: OK")
            if security == "starttls":
                if not server.has_extn("starttls"):
                    raise RuntimeError("Server does not advertise STARTTLS")
                server.starttls(context=context)
                server.ehlo()
                print("TLS upgrade: OK")
            if use_auth:
                server.login(required("SMTP_USERNAME"), required("SMTP_PASSWORD"))
                print("SMTP authentication: OK")
            else:
                print("SMTP authentication: skipped (SMTP_AUTH=false)")
            if args.send_to:
                envelope_from = required("SMTP_FROM_EMAIL")
                visible_from = args.from_email or envelope_from
                message = EmailMessage()
                message["From"] = visible_from
                message["To"] = args.send_to
                message["Subject"] = args.subject
                message.set_content(args.body)
                refused = server.send_message(message, from_addr=envelope_from)
                if refused:
                    raise RuntimeError("SMTP server refused the test recipient")
                print(f"Test email accepted for delivery to {args.send_to}")
            else:
                print("No email sent. Use --send-to ADDRESS for a delivery test.")
    except (OSError, smtplib.SMTPException, RuntimeError) as exc:
        raise SystemExit(f"SMTP probe failed: {type(exc).__name__}: {exc}") from None


if __name__ == "__main__":
    main()
