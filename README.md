# SMTP Relay API

Self-hosted HTTP API for sending email through your own SMTP account.

## Docker Compose

Create `docker-compose.yml`:

```yaml
services:
  smtp-relay:
    image: ghcr.io/samirkoirala/send-email:${SMTP_RELAY_VERSION:-1.1.1}
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "${PRIVATE_BIND_IP:-127.0.0.1}:8000:8000"
    read_only: true
    tmpfs:
      - /tmp:size=16m,mode=1777
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
```

Start the service:

```bash
cp .env.example .env
docker compose up -d
curl http://127.0.0.1:8000/readyz
```

## Environment

Create `.env`:

```env
PRIVATE_BIND_IP=127.0.0.1
SMTP_RELAY_VERSION=1.1.1
API_KEY=replace-with-output-of-openssl-rand-hex-32
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_AUTH=true
SMTP_USERNAME=no-reply@yourdomain.com
SMTP_PASSWORD=replace-with-app-password
SMTP_FROM_EMAIL=no-reply@yourdomain.com
SMTP_FROM_NAME=Your Company
ALLOWED_FROM_DOMAINS=yourdomain.com
SMTP_SECURITY=starttls
SMTP_TIMEOUT_SECONDS=15
LOG_LEVEL=INFO
DISABLE_DOCS=false
```

Generate `API_KEY` with:

```bash
openssl rand -hex 32
```

## Kubernetes

Edit the values in [`deploy/kubernetes.yaml`](deploy/kubernetes.yaml), then deploy:

```bash
kubectl apply -f deploy/kubernetes.yaml
kubectl rollout status deployment/smtp-relay
kubectl port-forward service/smtp-relay 8000:8000
curl http://127.0.0.1:8000/readyz
```
