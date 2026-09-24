# Self-hosting

SMTP Relay API is designed as a single-tenant service. Each operator runs an isolated container with an SMTP account and domains they control. It is not a centralized service that stores customer credentials.

## Deploy a released image

Download [`docker-compose.image.yml`](../docker-compose.image.yml) and [`.env.example`](../.env.example), then rename the environment file:

```bash
mv .env.example .env
openssl rand -hex 32
```

Put the generated value in `API_KEY`. Configure the SMTP account and restrict dynamic senders to domains you control:

```env
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_SECURITY=starttls
SMTP_AUTH=true
SMTP_USERNAME=no-reply@yourdomain.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=no-reply@yourdomain.com
SMTP_FROM_NAME=Your Company
ALLOWED_FROM_DOMAINS=yourdomain.com
```

Pin the image version and start it:

```bash
export SMTP_RELAY_VERSION=1.1.0
docker compose -f docker-compose.image.yml pull
docker compose -f docker-compose.image.yml up -d
curl --fail http://127.0.0.1:8000/readyz
```

Use a tag listed on the repository's Packages or Releases page. A tag is available after its matching Git tag has completed the publish workflow.

The release workflow publishes both AMD64 and ARM64 images. Repository maintainers must make the GHCR package public after its first publication so anonymous users can pull it.

## Sender behavior

`SMTP_FROM_EMAIL` is always used as the SMTP envelope sender. A request may provide a different visible `from_email` only when its domain appears in `ALLOWED_FROM_DOMAINS`.

This does not bypass an SMTP provider's policies. Some providers authorize every address on a verified domain; others require each address to exist as a mailbox or alias. Operators remain responsible for SPF, DKIM, DMARC, bounces, and provider limits.

## Kubernetes

[`deploy/kubernetes.yaml`](../deploy/kubernetes.yaml) is a secure baseline for an existing cluster. Replace the Secret and ConfigMap placeholders, pin an available image tag, then run:

```bash
kubectl apply -f deploy/kubernetes.yaml
kubectl rollout status deployment/smtp-relay
kubectl port-forward service/smtp-relay 8000:8000
curl --fail http://127.0.0.1:8000/readyz
```

Do not commit real values in the example Secret. Production clusters should source secrets from their established secret-management system. The included Service is intentionally private (`ClusterIP`).

## Network exposure

The image Compose file binds to `127.0.0.1` by default. Keep that default when the calling application is on the same host. For another host on a private network, set `PRIVATE_BIND_IP` to the relay server's private address and restrict TCP/8000 with a firewall.

Do not expose port 8000 directly to the public internet. Use the HTTPS deployment documented in the main README, keep the API key secret, and restrict source IPs where possible.

## Upgrade and rollback

Change `SMTP_RELAY_VERSION` to an immutable release tag, pull, and recreate the container. The service stores no data, so rollback consists of restoring the previous tag. Back up `.env` securely; it contains SMTP credentials.
