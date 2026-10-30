"""Messaging REST router (BE-1: P0 Stubs).

Provides Day-0 contract stubs for:
- POST /v1/conversations/{conversation_id}/messages
- GET /v1/sync/conversations
- GET /v1/conversations/{conversation_id}/messages

Allows Web, Mobile, and Member 3 (type generation) to integrate immediately.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.messaging.schemas import (
    ConversationSyncItem,
    GetMessagesResponse,
    MessageItem,
    SendMessageRequest,
    SendMessageResponse,
    SyncConversationsResponse,
)

router = APIRouter(prefix="/v1", tags=["messaging"])


@dataclass(frozen=True)
class AuthUserStub:
    """Day-0 stub for Member 2's AuthUser until app/auth/ is merged."""

    id: UUID
    tenant_id: UUID
    device_id: UUID


def get_current_user_stub(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthUserStub:
    """Dependency returning authenticated user or local dev default."""
    # Member 2 will provide the full production current_user.
    # For P0 Day-0 testing & local development, provide a stable deterministic stub.
    return AuthUserStub(
        id=UUID("0192df78-0000-7000-8000-000000000001"),
        tenant_id=UUID("0192df78-0000-7000-8000-000000000002"),
        device_id=UUID("0192df78-0000-7000-8000-000000000003"),
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message to a conversation (P0 stub)",
    description=(
        "Sends a text or media message to a conversation. "
        "Submitting the same client_msg_id will return the existing message idempotently."
    ),
)
def send_message_endpoint(
    conversation_id: UUID,
    payload: SendMessageRequest,
    user: Annotated[AuthUserStub, Depends(get_current_user_stub)],
) -> SendMessageResponse:
    """P0 stub for sending a message.

    Full transaction engine in app/send.py will be attached in P1.
    """
    if payload.kind == "text" and payload.body and len(payload.body) > 8000:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message body exceeds 8000 characters limit.",
        )

    # Return valid Pydantic response fulfilling the contract
    return SendMessageResponse(
        seq=1,
        id=uuid4(),
        created_at=datetime.now(UTC),
        duplicate=False,
    )


@router.get(
    "/sync/conversations",
    response_model=SyncConversationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync active conversations (P0 stub)",
    description="Returns all active conversation memberships and sync cursors for the authenticated user.",
)
def sync_conversations_endpoint(
    user: Annotated[AuthUserStub, Depends(get_current_user_stub)],
) -> SyncConversationsResponse:
    """P0 stub for syncing conversations and cursors."""
    mock_item = ConversationSyncItem(
        conversation_id=UUID("c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8"),
        last_seq=10,
        delivered_seq=10,
        read_seq=8,
        visible_from_seq=1,
    )
    return SyncConversationsResponse(conversations=[mock_item])


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=GetMessagesResponse,
    status_code=status.HTTP_200_OK,
    summary="List messages in conversation (P0 stub)",
    description="Returns messages in seq order after a given sequence number for catch-up.",
)
def get_messages_endpoint(
    conversation_id: UUID,
    after: Annotated[
        int, Query(ge=0, description="Retrieve messages strictly after this seq")
    ] = 0,
    limit: Annotated[int, Query(ge=1, le=200, description="Maximum messages to return")] = 50,
    user: Annotated[AuthUserStub, Depends(get_current_user_stub)] = None,
) -> GetMessagesResponse:
    """P0 stub for listing conversation messages."""
    now = datetime.now(UTC)
    mock_messages = [
        MessageItem(
            conversation_id=conversation_id,
            seq=after + 1,
            id=uuid4(),
            sender_id=user.id if user else UUID("0192df78-0000-7000-8000-000000000001"),
            client_msg_id=uuid4(),
            kind="text",
            target_seq=None,
            body="Welcome to Varta Bharat!",
            attachment_id=None,
            enc_scheme=0,
            created_at=now,
        )
    ]
    return GetMessagesResponse(
        messages=mock_messages,
        has_more=False,
        last_seq=after + 1,
    )
