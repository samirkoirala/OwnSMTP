# Contributing

Contributions are welcome through GitHub issues and pull requests.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

## Pull requests

- Keep changes focused and explain their motivation.
- Add or update tests for behavior changes.
- Run the test suite before submitting.
- Do not include credentials, `.env` files, real email addresses, or production hostnames.
- Update the README when configuration or user-facing behavior changes.

For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
