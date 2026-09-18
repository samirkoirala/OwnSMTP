# SMTP Relay API

A small authenticated HTTP API for sending email through a trusted SMTP server. It is useful when an application host cannot make outbound SMTP connections but can reach another host over HTTP or HTTPS.

```text
Application → HTTP(S) API → SMTP Relay API → SMTP server → Recipient
```

The gateway supports SMTP over implicit TLS, STARTTLS, authenticated SMTP, and trusted local relays. Callers can set recipients, subject, plain-text or HTML content, and an optional reply-to address. SMTP credentials and the sender identity remain on the gateway host.

## Features

- API-key authentication
- SMTP SSL, STARTTLS, and unencrypted local-relay modes
- Plain-text and HTML messages
- Multiple recipients with validation and request limits
- Container runs as a non-root user with a read-only filesystem
- Private-network deployment or public HTTPS deployment with source-IP filtering
- Health and readiness endpoints
- Standalone SMTP connectivity probe

## Quick start

Requirements: Docker with the Compose plugin.

```bash
cp .env.example .env
openssl rand -hex 32
```

Put the generated value in `API_KEY`, then configure the SMTP settings in `.env`.

```bash
docker compose up -d --build
curl --fail http://127.0.0.1:8000/readyz
```

Send an email:

```bash
curl --fail-with-body \
  -X POST http://127.0.0.1:8000/send-email \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: YOUR_API_KEY' \
  -d '{
    "recipient_email": ["recipient@example.com"],
    "subject": "Gateway test",
    "body": "<p>The SMTP relay API is working.</p>",
    "body_type": "html"
  }'
```

Successful submission returns:

```json
{"status":"success","message":"Email accepted by SMTP server"}
```

Acceptance means the SMTP server accepted the message. Final delivery can still be affected by bounces, spam filtering, SPF, DKIM, and DMARC.

## Configuration

| Variable | Required | Default | Description |
|---|---:|---|---|
| `API_KEY` | Yes | — | API credential, at least 32 characters |
| `SMTP_HOST` | Yes | — | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_AUTH` | No | `true` | Whether SMTP authentication is enabled |
| `SMTP_USERNAME` | If auth | — | SMTP username |
| `SMTP_PASSWORD` | If auth | — | SMTP password or app password |
| `SMTP_FROM_EMAIL` | Yes | — | Envelope and visible sender address |
| `SMTP_FROM_NAME` | No | `Notification Service` | Visible sender name |
| `SMTP_SECURITY` | No | `starttls` | `starttls`, `ssl`, or `none` |
| `SMTP_TIMEOUT_SECONDS` | No | `15` | SMTP operation timeout |
| `PRIVATE_BIND_IP` | No | `127.0.0.1` | Host address used by the private Compose stack |
| `DISABLE_DOCS` | No | `false` | Disable `/docs` when set to `true` |
| `LOG_LEVEL` | No | `INFO` | Application log level |

Common SMTP combinations:

| Mode | Typical port | `SMTP_SECURITY` |
|---|---:|---|
| Submission with STARTTLS | 587 | `starttls` |
| Implicit TLS | 465 | `ssl` |
| Trusted local relay | 25 | `none` |

Never commit `.env` or SMTP credentials.

## API

### `POST /send-email`

Requires the `X-API-Key` header.

```json
{
  "recipient_email": ["one@example.com", "two@example.com"],
  "subject": "Hello",
  "body": "<h1>Hello</h1>",
  "body_type": "html",
  "reply_to": "support@example.com"
}
```

`body_type` defaults to `html`. `reply_to` is optional. Requests are limited to 50 recipients, a 255-character subject, and a 1 MB body.

| Status | Meaning |
|---:|---|
| `200` | SMTP server accepted the message |
| `401` | API key is missing or invalid |
| `422` | Request validation failed |
| `502` | SMTP connection, authentication, or submission failed |
| `503` | Gateway configuration is incomplete |

### Health endpoints

- `GET /healthz` confirms the process is alive.
- `GET /readyz` validates required configuration without connecting to SMTP.

## Deployment

### Private network — recommended

Use this when both hosts share a VPC, VPN, or other trusted network.

1. Set `PRIVATE_BIND_IP` to the gateway host's private address.
2. Allow TCP/8000 only from the application host's private address.
3. Run `docker compose up -d --build`.
4. Configure the application with `http://PRIVATE_IP:8000` and the API key.

Private networking keeps the API and message contents off the public internet and requires fewer moving parts.

### Public network with HTTPS

Use [docker-compose.public.yml](docker-compose.public.yml) when private connectivity is unavailable.

1. Point a DNS hostname to the gateway host's public IP.
2. Set `GATEWAY_DOMAIN` to that hostname.
3. Set `APP_VM_PUBLIC_IP` to the calling application's fixed public IP.
4. Allow inbound TCP/80 and TCP/443. Do not expose TCP/8000.
5. Start the public stack:

```bash
docker compose -f docker-compose.public.yml up -d --build
docker compose -f docker-compose.public.yml logs --tail=100
```

Caddy obtains and renews the HTTPS certificate, rejects requests from other source IPs, and proxies permitted requests to the unexposed gateway container. The API key provides a second authentication layer.

Use `https://your-gateway.example.com` from the application host. Avoid exposing `http://PUBLIC_IP:8000`; plain HTTP reveals API keys and message contents in transit.

## SMTP verification

Test connectivity, TLS, and authentication without sending a message:

```bash
python3 smtp_probe.py
```

Send one real test message:

```bash
python3 smtp_probe.py \
  --send-to recipient@example.com \
  --subject "Gateway test" \
  --body "SMTP delivery submission worked."
```

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

## License

Licensed under the [MIT License](LICENSE).
