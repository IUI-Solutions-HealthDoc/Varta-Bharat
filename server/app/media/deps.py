"""TEMPORARY auth placeholder. Replace this import with the real current_user from
app.auth once it lands (AuthUser(id, tenant_id, device_id)). Only works when
ENVIRONMENT=local."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Header, HTTPException

from app.config import settings


@dataclass(frozen=True)
class AuthUser:
    id: UUID
    tenant_id: UUID
    device_id: UUID | None = None


def current_user(
    x_dev_user_id: Annotated[UUID | None, Header()] = None,
    x_dev_tenant_id: Annotated[UUID | None, Header()] = None,
) -> AuthUser:
    if settings.environment != "local" or x_dev_user_id is None or x_dev_tenant_id is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return AuthUser(id=x_dev_user_id, tenant_id=x_dev_tenant_id)