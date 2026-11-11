
import psycopg
from fastapi import HTTPException

from app.auth.dependencies import AuthUser
from app.conversations.schemas import ConversationCreate


def create_conversation(
    conn: psycopg.Connection,
    user: AuthUser,
    body: ConversationCreate,
) -> dict:

    # Verify that the user is active and belongs to this tenant.
    membership = conn.execute(
        """
        SELECT 1
        FROM users AS u
        JOIN tenant_members AS tm ON tm.user_id = u.id
        WHERE u.id = %s
          AND tm.tenant_id = %s
          AND u.status = 'active'
          AND tm.removed_at IS NULL
        FOR SHARE OF u, tm
        """,
        (user.id, user.tenant_id),
    ).fetchone()

    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="Active tenant membership required",
        )

    # If a community is supplied, verify that it belongs to this tenant.
    if body.community_id is not None:
        community = conn.execute(
            """
            SELECT id
            FROM communities
            WHERE id = %s AND tenant_id = %s
            FOR SHARE
            """,
            (body.community_id, user.tenant_id),
        ).fetchone()

        if community is None:
            raise HTTPException(
                status_code=404,
                detail="Community not found",
            )

    # Create the conversation.
    row = conn.execute(
        """
        INSERT INTO conversations (
            tenant_id,
            community_id,
            kind,
            title,
            created_by
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, tenant_id, kind, title, created_by, created_at
        """,
        (
            user.tenant_id,
            body.community_id,
            body.kind,
            body.title,
            user.id,
        ),
    ).fetchone()

    # Add the creator as the conversation administrator.
    conn.execute(
        """
        INSERT INTO conversation_members (
            conversation_id,
            user_id,
            role
        )
        VALUES (%s, %s, 'admin')
        """,
        (row[0], user.id),
    )

    return {
        "id": row[0],
        "tenant_id": row[1],
        "kind": row[2],
        "title": row[3],
        "created_by": row[4],
        "created_at": row[5],
    }