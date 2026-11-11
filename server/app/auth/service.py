
from uuid import UUID

import psycopg

from app.auth.authorization import Action, authorize as check_permission
from app.auth.dependencies import AuthUser
from app.auth.repository import get_conversation_access


def authorize(
    conn: psycopg.Connection,
    user: AuthUser,
    action: Action,
    conversation_id: UUID,
) -> None:
    """
    Load access information and enforce permissions
    using the caller's existing database connection.

    The caller must invoke this inside the transaction
    protecting the operation.
    """

    access = get_conversation_access(
        conn=conn,
        user_id=user.id,
        tenant_id=user.tenant_id,
        conversation_id=conversation_id,
    )

    check_permission(
        user=user,
        action=action,
        conversation_id=conversation_id,
        access=access,
    )
 