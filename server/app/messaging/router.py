"""Messaging REST router (BE-1: P1 Core Engine).

Implements:
- POST /v1/conversations/{conversation_id}/messages
- GET /v1/sync/conversations
- GET /v1/conversations/{conversation_id}/messages
- DELETE /v1/conversations/{conversation_id}/messages/{target_seq}
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, status

from app.auth.dependencies import AuthUser, current_user
from app.auth.service import authorize
from app.core.db import get_conn
from app.media.validation import AttachmentRejected
from app.messaging.schemas import (
    ConversationSyncItem,
    DeleteMessageResponse,
    GetMessagesResponse,
    MessageItem,
    SendMessageRequest,
    SendMessageResponse,
    SyncConversationsResponse,
)
from app.send import NotAllowed, send_message, send_tombstone

router = APIRouter(prefix="/v1", tags=["messaging"])


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message to a conversation",
    description=(
        "Sends a text or media message to a conversation. "
        "Submitting the same client_msg_id will return the existing message idempotently."
    ),
)
def send_message_endpoint(
    conversation_id: UUID,
    payload: SendMessageRequest,
    user: Annotated[AuthUser, Depends(current_user)],
) -> SendMessageResponse:
    """Send a message using the hardened transactional engine in app/send.py."""
    if payload.kind == "text" and payload.body and len(payload.body) > 8000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message body exceeds 8000 characters limit.",
        )
    if payload.body is not None and "\x00" in payload.body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message body cannot contain NUL bytes.",
        )

    with get_conn() as conn:
        try:
            sent = send_message(
                conn,
                conversation_id=conversation_id,
                sender_id=user.id,
                tenant_id=user.tenant_id,
                client_msg_id=payload.client_msg_id,
                kind=payload.kind,
                body=payload.body,
                attachment_id=payload.attachment_id,
            )
        except (NotAllowed, AttachmentRejected) as exc:
            msg = str(exc)
            if "not found" in msg.lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

    return SendMessageResponse(
        seq=sent.seq,
        id=sent.id,
        created_at=sent.created_at,
        duplicate=sent.duplicate,
    )


@router.get(
    "/sync/conversations",
    response_model=SyncConversationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync active conversations",
    description="Returns all active conversation memberships and sync cursors for the authenticated user.",
)
def sync_conversations_endpoint(
    user: Annotated[AuthUser, Depends(current_user)],
) -> SyncConversationsResponse:
    """List active conversations with last_seq, delivered_seq, read_seq, visible_from_seq."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT cm.conversation_id, c.last_seq, cm.delivered_seq, cm.read_seq, cm.visible_from_seq
            FROM conversation_members cm
            JOIN conversations c ON c.id = cm.conversation_id
            JOIN tenant_members tm ON tm.tenant_id = c.tenant_id AND tm.user_id = cm.user_id
            JOIN users u ON u.id = cm.user_id
            WHERE cm.user_id = %s
              AND c.tenant_id = %s
              AND cm.left_at IS NULL
              AND tm.removed_at IS NULL
              AND u.status = 'active'
            ORDER BY c.created_at DESC
            """,
            (user.id, user.tenant_id),
        ).fetchall()

    items = [
        ConversationSyncItem(
            conversation_id=r[0],
            last_seq=r[1],
            delivered_seq=r[2],
            read_seq=r[3],
            visible_from_seq=r[4],
        )
        for r in rows
    ]
    return SyncConversationsResponse(conversations=items)


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=GetMessagesResponse,
    status_code=status.HTTP_200_OK,
    summary="List messages in conversation",
    description="Returns messages in seq order after a given sequence number for catch-up.",
)
def get_messages_endpoint(
    conversation_id: UUID,
    user: Annotated[AuthUser, Depends(current_user)],
    after: Annotated[int, Query(ge=0, description="Retrieve messages strictly after this seq")] = 0,
    limit: Annotated[int, Query(ge=1, le=200, description="Maximum messages to return")] = 50,
) -> GetMessagesResponse:
    """Fetch paginated messages respecting Invariant I4 (visibility and left/inactive conversations)."""
    user_id = user.id

    with get_conn() as conn:
        authorize(conn, user, "read", conversation_id)

        member = conn.execute(
            """
            SELECT cm.visible_from_seq, cm.left_at
            FROM conversation_members cm
            WHERE cm.conversation_id = %s AND cm.user_id = %s
            """,
            (conversation_id, user_id),
        ).fetchone()

        if member is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a member of this conversation",
            )

        visible_from_seq, left_at = member
        if left_at is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has left this conversation (Invariant I4)",
            )

        # Invariant I4: never return seq < visible_from_seq
        effective_after = max(after, visible_from_seq - 1)

        rows = conn.execute(
            """
            SELECT conversation_id, seq, id, sender_id, client_msg_id, kind, target_seq,
                   body, attachment_id, enc_scheme, created_at
            FROM messages
            WHERE conversation_id = %s AND seq > %s
            ORDER BY seq ASC
            LIMIT %s
            """,
            (conversation_id, effective_after, limit + 1),
        ).fetchall()

    has_more = len(rows) > limit
    returned_rows = rows[:limit]

    messages = [
        MessageItem(
            conversation_id=r[0],
            seq=r[1],
            id=r[2],
            sender_id=r[3],
            client_msg_id=r[4],
            kind=r[5],
            target_seq=r[6],
            body=r[7],
            attachment_id=r[8],
            enc_scheme=r[9],
            created_at=r[10],
        )
        for r in returned_rows
    ]

    highest_seq = messages[-1].seq if messages else after
    return GetMessagesResponse(
        messages=messages,
        has_more=has_more,
        last_seq=highest_seq,
    )


@router.delete(
    "/conversations/{conversation_id}/messages/{target_seq}",
    response_model=DeleteMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a message (tombstone)",
    description=(
        "Appends a tombstone message deletion (kind='delete', target_seq=target_seq). "
        "The message row is never deleted from the database (Invariant I6). "
        "Only the original message sender or a conversation admin may delete a message."
    ),
)
def delete_message_endpoint(
    conversation_id: UUID,
    target_seq: Annotated[int, Path(ge=1, description="Sequence number of message to delete")],
    user: Annotated[AuthUser, Depends(current_user)],
    x_idempotency_key: Annotated[str | None, Header()] = None,
) -> DeleteMessageResponse:
    """Tombstone message deletion endpoint."""
    client_msg_id = None
    if x_idempotency_key:
        try:
            client_msg_id = UUID(x_idempotency_key)
        except ValueError:
            pass

    with get_conn() as conn:
        try:
            sent = send_tombstone(
                conn,
                conversation_id=conversation_id,
                actor_id=user.id,
                tenant_id=user.tenant_id,
                target_seq=target_seq,
                client_msg_id=client_msg_id,
            )
        except NotAllowed as exc:
            msg = str(exc)
            if "not found" in msg.lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg) from exc
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

    return DeleteMessageResponse(
        seq=sent.seq,
        id=sent.id,
        target_seq=target_seq,
        kind="delete",
        created_at=sent.created_at,
    )
