import pytest
from fastapi import HTTPException

from email_gateway.config import Settings
from email_gateway.security import require_api_key


def test_api_key_is_required(settings: Settings):
    with pytest.raises(HTTPException) as error:
        require_api_key(None, settings)
    assert error.value.status_code == 401
    assert error.value.headers == {"WWW-Authenticate": "ApiKey"}


def test_valid_api_key_is_accepted(settings: Settings):
    require_api_key("a" * 64, settings)
