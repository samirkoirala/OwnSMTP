# Operations guide

## Production checklist

- Generate `API_KEY` with at least 32 random bytes and store it in a secret manager.
- Use `SMTP_SECURITY=starttls` or `ssl`; reserve `none` for a trusted local relay.
- Bind to a private network, or use the public Compose stack with HTTPS and an IP allow list.
- Keep `/docs` disabled unless API discovery is intentionally public.
- Pin deployments to a versioned image tag; avoid `latest` for production rollouts.
- Configure SMTP-provider SPF, DKIM, and DMARC records for the sender domain.
- Alert on sustained HTTP 5xx responses and container readiness failures.

## Rollout and verification

1. Pull or build the desired version.
2. Run `docker compose config` to validate interpolation.
3. Start the service and wait for `/readyz` to return `200`.
4. Run `python3 smtp_probe.py` to verify connection, TLS, and authentication.
5. Send one real message to a controlled inbox and verify delivery.

The liveness endpoint (`/healthz`) only confirms that the process is responding. The readiness endpoint (`/readyz`) confirms that required configuration is valid; it intentionally does not contact SMTP on every probe.

## Monitoring

Application logs go to standard output and never intentionally include credentials or message bodies. Every HTTP response contains `X-Request-ID`; callers may supply this header to correlate their own logs. Monitor at least:

- response count and latency by status code;
- `502` SMTP failures;
- container restarts and readiness failures;
- SMTP-provider rejection, bounce, and reputation metrics.

## Scaling and delivery guarantees

Each Uvicorn worker sends synchronously and holds no durable state. Multiple replicas are safe because all configuration is read-only, but SMTP-provider connection and rate limits still apply. An HTTP `200` means the upstream SMTP server accepted the message, not that the recipient received it.

The relay has no durable queue and does not automatically retry ambiguous failures. Automatic retries at this layer could send duplicates if the SMTP server accepted a message before the connection failed. Clients that require at-least-once delivery should use stable application message IDs and a durable queue with an explicit retry policy.

## Backup and rollback

The service stores no application data, so only secret-manager configuration and deployment manifests require backup. To roll back, deploy the preceding immutable image tag and verify `/readyz`; no data migration is required.

For the supported released-image workflow, see [docs/SELF_HOSTING.md](docs/SELF_HOSTING.md).
