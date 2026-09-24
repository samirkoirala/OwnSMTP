# SMTP Relay API

A self-hosted HTTP-to-SMTP gateway for applications. Run one container with your own SMTP account, keep credentials out of application code, and expose a small authenticated API for transactional email.

```text
Application → HTTP(S) API → SMTP Relay API → SMTP server → Recipient
```

Each deployment is single-tenant: operators bring their own SMTP provider and control which sender domains are allowed. The project does not host customer accounts or store credentials centrally.

## Features

- API-key authentication
- SMTP SSL, STARTTLS, and unencrypted local-relay modes
- Plain-text and HTML messages
- Multiple recipients with validation and request limits
- Container runs as a non-root user with a read-only filesystem
- Private-network deployment or public HTTPS deployment with source-IP filtering
- Health and readiness endpoints
- Standalone SMTP connectivity probe
- Versioned API route with backward-compatible legacy route
- Request correlation IDs and baseline browser security headers
- CI checks for tests, coverage, linting, typing, and container builds
- Tagged container releases through GitHub Container Registry
- Interactive OpenAPI documentation at `/docs`

## Quick start

Requirements: Docker with the Compose plugin. To deploy a published image without cloning the source:

```bash
curl -O https://raw.githubusercontent.com/samirkoirala/send-email/main/docker-compose.image.yml
curl -O https://raw.githubusercontent.com/samirkoirala/send-email/main/.env.example
mv .env.example .env
```

Alternatively, clone the repository to build the image locally. In either case:

```bash
cp .env.example .env
openssl rand -hex 32
```

Put the generated value in `API_KEY`, then configure the SMTP settings in `.env`.

For local Python development, the service automatically loads `.env` from the working directory.

```bash
docker compose -f docker-compose.image.yml up -d
curl --fail http://127.0.0.1:8000/readyz
```

Open `http://127.0.0.1:8000/docs` for interactive API documentation. See the complete [self-hosting guide](docs/SELF_HOSTING.md) before production deployment.

Send an email:

```bash
curl --fail-with-body \
  -X POST http://127.0.0.1:8000/v1/emails \
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
| `ALLOWED_FROM_DOMAINS` | No | Domain of `SMTP_FROM_EMAIL` | Comma-separated domains permitted for request-level senders |
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

### `POST /v1/emails`

Requires the `X-API-Key` header.

`POST /send-email` remains available for backward compatibility. New clients should use the versioned route.

```json
{
  "recipient_email": ["one@example.com", "two@example.com"],
  "subject": "Hello",
  "body": "<h1>Hello</h1>",
  "body_type": "html",
  "from_email": "notifications@example.com",
  "from_name": "Example Notifications",
  "reply_to": "support@example.com"
}
```

`body_type` defaults to `html`. `from_email`, `from_name`, and `reply_to` are optional. When `from_email` is supplied, its domain must be listed in `ALLOWED_FROM_DOMAINS`. The configured `SMTP_FROM_EMAIL` remains the SMTP envelope sender for provider verification and bounce handling. Requests are limited to 50 recipients, a 255-character subject, and a 1 MB body.

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

This service sends during the HTTP request and returns only after the SMTP server accepts or rejects the message. That is a good fit for low-to-moderate transactional traffic. If clients need durable asynchronous delivery, retries across restarts, per-tenant quotas, or delivery history, place a durable queue in front of the relay or use a queue-backed mail platform.

The recommended deployment consumes an immutable image from `ghcr.io/samirkoirala/send-email`. Tagged releases publish automatically through GitHub Actions; operators should pin a version instead of using `latest` in production.

### Docker Compose

Download the image-based Compose file and environment template:

```bash
curl -O https://raw.githubusercontent.com/samirkoirala/send-email/main/docker-compose.image.yml
curl -O https://raw.githubusercontent.com/samirkoirala/send-email/main/.env.example
mv .env.example .env
```

Generate an API key and put it in `.env`, then configure your SMTP account and allowed domains:

```bash
openssl rand -hex 32
docker compose -f docker-compose.image.yml pull
docker compose -f docker-compose.image.yml up -d
curl --fail http://127.0.0.1:8000/readyz
```

Set `SMTP_RELAY_VERSION` to an available immutable release tag in production. The container binds to `127.0.0.1` by default.

The provided `.env.example` currently pins `ghcr.io/samirkoirala/send-email:1.1.1`. Confirm the GHCR package is public before expecting anonymous hosts to pull it.

### Kubernetes

The included [Kubernetes manifest](deploy/kubernetes.yaml) provides:

- separate Secret and ConfigMap resources;
- two stateless replicas behind a ClusterIP Service;
- liveness and readiness probes;
- CPU and memory constraints;
- a non-root, read-only container without Linux capabilities or a service-account token.

Download the manifest, replace all placeholder values, and pin an available image version:

```bash
curl -O https://raw.githubusercontent.com/samirkoirala/send-email/main/deploy/kubernetes.yaml
# Edit kubernetes.yaml before applying it.
kubectl apply -f kubernetes.yaml
kubectl rollout status deployment/smtp-relay
kubectl port-forward service/smtp-relay 8000:8000
curl --fail http://127.0.0.1:8000/readyz
```

The example Secret uses `stringData` for readability and must not be committed after inserting credentials. For production, create the Secret through your secret manager, Sealed Secrets, External Secrets, or an equivalent system. Keep the Service private; if external access is necessary, add an HTTPS Ingress with source restrictions rather than changing it to an unrestricted `LoadBalancer`.

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

### Project structure

```text
email_gateway/
├── api.py        # HTTP routes and error mapping
├── app.py        # application factory and middleware
├── config.py     # environment parsing and validation
├── mailer.py     # SMTP connection and message delivery
├── schemas.py    # public request/response contracts
└── security.py   # API-key authentication
```

Run every local quality check used by CI:

```bash
ruff check .
ruff format --check .
mypy
pytest --cov
docker build -t smtp-relay-api:local .
```

See [OPERATIONS.md](OPERATIONS.md) for production rollout, monitoring, backup, and rollback guidance. Releases are documented in [CHANGELOG.md](CHANGELOG.md).

## License

Licensed under the [MIT License](LICENSE).
