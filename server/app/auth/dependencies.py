from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from app.auth.security import decode_access_token
from app.core.db import get_conn


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthUser:
    id: UUID
    tenant_id: UUID
    device_id: UUID


def current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
) -> AuthUser:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)

        user = AuthUser(
            id=UUID(payload["sub"]),
            tenant_id=UUID(payload["tenant_id"]),
            device_id=UUID(payload["device_id"]),
        )

    except (InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    with get_conn() as conn:
        device = conn.execute(
            """
            SELECT 1
            FROM devices
            WHERE id = %s
              AND user_id = %s
              AND revoked_at IS NULL
            """,
            (user.device_id, user.id),
        ).fetchone()

    if device is None:
        raise HTTPException(
            status_code=401,
            detail="Device session is invalid or revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
