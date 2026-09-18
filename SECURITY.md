# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities through GitHub's private vulnerability reporting feature for this repository. Do not open a public issue containing exploit details, credentials, or private infrastructure information.

Include the affected version or commit, reproduction steps, impact, and any suggested mitigation. Maintainers will acknowledge the report as soon as practical and coordinate disclosure after a fix is available.

## Deployment responsibility

This service handles SMTP credentials and arbitrary email content. Operators should keep credentials outside source control, restrict network access, use HTTPS across public networks, rotate API keys, monitor logs, and keep container images and dependencies updated.
