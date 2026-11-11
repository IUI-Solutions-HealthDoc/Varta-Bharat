from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status

from app.auth.dependencies import AuthUser


Action = Literal[
    "read",
    "send",
    "manage_members",
    "manage_settings",
]


@dataclass(frozen=True)
class ConversationAccess:
    tenant_id: UUID
    kind: str
    member_role: str | None
    left_at: datetime | None
    user_status: str
    tenant_member_active: bool


def authorize(
    user: AuthUser,
    action: Action,
    conversation_id: UUID,
    access: ConversationAccess | None,
) -> None:
    """Enforce tenant, account, membership and role permissions."""

    # 1. Hide conversations that do not exist or belong to another tenant.
    if access is None or user.tenant_id != access.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    # 2. Account and tenant membership must always be active.
    if access.user_status != "active" or not access.tenant_member_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account or tenant membership is not active",
        )

    # 3. Public and announcement conversations can be read
    # by any active member of the same tenant.
    if action == "read" and access.kind in ("public", "announcement"):
        return

    # 4. Other actions require active conversation membership.
    if access.member_role is None or access.left_at is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not an active member of this conversation",
        )

    is_admin = access.member_role == "admin"

    # 5. Active conversation members can read.
    if action == "read":
        return

    # 6. Announcement conversations only allow admins to send.
    if action == "send":
        if access.kind == "announcement" and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can send in announcement conversations",
            )
        return

    # 7. Only conversation admins can manage members or settings.
    if action in ("manage_members", "manage_settings"):
        if not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permission required",
            )
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported authorization action",
    )
