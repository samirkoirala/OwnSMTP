from fastapi.testclient import TestClient

from email_gateway.app import create_app
from email_gateway.config import Settings, get_settings
from email_gateway.mailer import MailDeliveryError, SMTPMailer


def test_health_endpoint_adds_security_and_request_headers():
    with TestClient(create_app()) as client:
        response = client.get("/healthz", headers={"X-Request-ID": "test-request"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Request-ID"] == "test-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"


def test_landing_page_and_stylesheet_are_served():
    with TestClient(create_app()) as client:
        landing = client.get("/")
        stylesheet = client.get("/assets/site.css")

    assert landing.status_code == 200
    assert "Your SMTP server" in landing.text
    assert "Deploy with Docker or Kubernetes" in landing.text
    assert stylesheet.status_code == 200
    assert "--green" in stylesheet.text


def test_versioned_email_endpoint(settings: Settings, monkeypatch):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(SMTPMailer, "send", lambda self, request: None)

    with TestClient(app) as client:
        unauthorized = client.post(
            "/v1/emails",
            json={"recipient_email": ["person@example.com"], "subject": "Test", "body": "Hello"},
        )
        accepted = client.post(
            "/v1/emails",
            headers={"X-API-Key": "a" * 64},
            json={"recipient_email": ["person@example.com"], "subject": "Test", "body": "Hello"},
        )

    assert unauthorized.status_code == 401
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "success"


def test_delivery_failure_is_mapped_to_bad_gateway(settings: Settings, monkeypatch):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    def fail_delivery(self, request):
        raise MailDeliveryError("SMTP failed")

    monkeypatch.setattr(SMTPMailer, "send", fail_delivery)
    with TestClient(app) as client:
        response = client.post(
            "/send-email",
            headers={"X-API-Key": "a" * 64},
            json={"recipient_email": ["person@example.com"], "subject": "Test", "body": "Hello"},
        )

    assert response.status_code == 502
    assert response.json() == {"detail": "Email delivery failed"}


def test_sender_outside_allowlist_is_rejected(settings: Settings):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings

    with TestClient(app) as client:
        response = client.post(
            "/v1/emails",
            headers={"X-API-Key": "a" * 64},
            json={
                "recipient_email": ["person@example.com"],
                "subject": "Test",
                "body": "Hello",
                "from_email": "attacker@outside.example",
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "Sender domain is not allowed"}
