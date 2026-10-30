
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from app.config import settings


def create_access_token(
    user_id: str,
    tenant_id: str,
    device_id: str,
) -> str:
    """
    Create a signed JWT access token for an authenticated user.
    """

    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "device_id": device_id,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "token_type": "access",
    }

    token = jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    return token


def decode_access_token(token: str) -> dict:
    """
    Verify a JWT and return its claims.
    Raises InvalidTokenError if the token is invalid or expired.
    """

    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={
            "require": [
                "sub",
                "tenant_id",
                "device_id",
                "jti",
                "iat",
                "exp",
                "iss",
                "aud",
                "token_type",
            ]
        },
    )

    if payload["token_type"] != "access":
        raise InvalidTokenError("Invalid token type")

    return payload
