
from uuid import UUID

import psycopg

from app.auth.authorization import ConversationAccess


def get_conversation_access(
    conn: psycopg.Connection,
    user_id: UUID,
    tenant_id: UUID,
    conversation_id: UUID,
) -> ConversationAccess | None:
    """
    Fetch the user's account, tenant membership and conversation membership.
    """

    row = conn.execute(
        """
        SELECT
            c.tenant_id,
            c.kind,
            cm.role,
            cm.left_at,
            u.status,
            (tm.user_id IS NOT NULL AND tm.removed_at IS NULL)
                AS tenant_member_active
        FROM conversations AS c
        LEFT JOIN conversation_members AS cm
            ON cm.conversation_id = c.id
            AND cm.user_id = %s
        LEFT JOIN users AS u
            ON u.id = %s
        LEFT JOIN tenant_members AS tm
            ON tm.tenant_id = c.tenant_id
            AND tm.user_id = %s
        WHERE c.id = %s
          AND c.tenant_id = %s
        """,
        (user_id, user_id, user_id, conversation_id, tenant_id),
    ).fetchone()

    if row is None:
        return None

    return ConversationAccess(
        tenant_id=row[0],
        kind=row[1],
        member_role=row[2],
        left_at=row[3],
        user_status=row[4] or "missing",
        tenant_member_active=row[5],
    )
