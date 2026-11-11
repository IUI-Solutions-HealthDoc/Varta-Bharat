import pytest
from pydantic import ValidationError

from app.config import EXAMPLE_JWT_SECRET, Settings

STRONG = "s" * 48


def test_local_allows_short_secret():
    assert Settings(environment="local", jwt_secret="short").jwt_secret == "short"


def test_local_allows_example_secret():
    assert Settings(environment="local", jwt_secret=EXAMPLE_JWT_SECRET)


def test_non_local_rejects_short_secret():
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(environment="production", jwt_secret="x" * 31)


def test_non_local_rejects_example_secret():
    with pytest.raises(ValidationError, match=".env.example"):
        Settings(environment="production", jwt_secret=EXAMPLE_JWT_SECRET)


def test_non_local_accepts_strong_secret():
    assert Settings(environment="staging", jwt_secret=STRONG).jwt_secret == STRONG
