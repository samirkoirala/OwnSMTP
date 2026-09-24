# Changelog

All notable changes are documented here. This project follows Semantic Versioning.

## [Unreleased]

## [1.1.1] - 2026-09-24

### Changed

- Removed the marketing landing page and static assets to keep the runtime image API-only.
- Kept generated OpenAPI documentation at `/docs` and deployment guidance in the repository.

## [1.1.0] - 2026-09-24

### Added

- Allow-listed request-level sender addresses while retaining the configured SMTP envelope sender.
- Built-in project landing page and a documented versioned-image self-hosting workflow.
- Docker Compose and hardened Kubernetes deployment guides on the landing page and in repository documentation.
- Modular `email_gateway` application package and application factory.
- Versioned `POST /v1/emails` API alias.
- Request IDs, baseline security headers, strict linting, typing, and coverage checks.
- Automated dependency updates and tagged GHCR container releases.

### Changed

- HTML mail now includes a plain-text fallback.
- STARTTLS mode fails closed when the server does not advertise STARTTLS.

## [1.0.0] - 2026-09-18

- Initial open-source release.

[Unreleased]: https://github.com/samirkoirala/send-email/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/samirkoirala/send-email/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/samirkoirala/send-email/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/samirkoirala/send-email/releases/tag/v1.0.0
