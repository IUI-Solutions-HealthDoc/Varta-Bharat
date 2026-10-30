"""Pydantic request and response models for Varta Bharat Messaging API (BE-1).

These models define the contracts for REST messaging endpoints as specified in
Plan v2 section 7.2 and docs/protocol.md. They are exported for OpenAPI documentation
and automatic TypeScript type generation.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SendMessageRequest(BaseModel):
    """Payload for submitting a message to a conversation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "client_msg_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
                "kind": "text",
                "body": "Namaste Bharat! This is our first message.",
                "attachment_id": None,
                "enc_scheme": 0,
            }
        }
    )

    client_msg_id: Annotated[
        UUID,
        Field(description="Client-generated unique ID for idempotent deduplication."),
    ]
    kind: Annotated[
        Literal["text", "media"],
        Field(
            default="text",
            description="Message kind. Clients may only submit 'text' or 'media'.",
        ),
    ]
    body: Annotated[
        str | None,
        Field(
            default=None,
            max_length=8000,
            description="Message body text (max 8000 characters). Normalized to NFC.",
        ),
    ]
    attachment_id: Annotated[
        UUID | None,
        Field(
            default=None,
            description="ID of a pre-uploaded attachment in ready state. Required for media.",
        ),
    ]
    enc_scheme: Annotated[
        int,
        Field(
            default=0,
            ge=0,
            description="Encryption scheme identifier (0 = plaintext / server-managed).",
        ),
    ]

    @model_validator(mode="after")
    def validate_content_payload(self) -> "SendMessageRequest":
        if self.kind == "text" and (self.body is None or not self.body.strip()):
            raise ValueError("Text messages must include a non-empty body.")
        if self.kind == "media" and self.attachment_id is None:
            raise ValueError("Media messages must provide an attachment_id.")
        return self


class SendMessageResponse(BaseModel):
    """Response returned upon successful message submission or idempotent retry."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "seq": 42,
                "id": "0192df78-8bc4-7123-93df-520e5e4860b0",
                "created_at": "2026-10-30T10:15:30.123456Z",
                "duplicate": False,
            }
        }
    )

    seq: Annotated[int, Field(ge=1, description="Strictly gapless monotonic sequence number.")]
    id: Annotated[UUID, Field(description="Server-assigned UUIDv7 of the message.")]
    created_at: Annotated[datetime, Field(description="Timestamp when message was stored.")]
    duplicate: Annotated[
        bool,
        Field(
            default=False,
            description="True if this send was an idempotent retry of an existing message.",
        ),
    ]


class ConversationSyncItem(BaseModel):
    """Per-conversation synchronization status and cursors for an active member."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
                "last_seq": 150,
                "delivered_seq": 148,
                "read_seq": 140,
                "visible_from_seq": 1,
            }
        }
    )

    conversation_id: Annotated[UUID, Field(description="Unique ID of the conversation.")]
    last_seq: Annotated[int, Field(ge=0, description="Highest committed sequence in the chat.")]
    delivered_seq: Annotated[int, Field(ge=0, description="Last sequence confirmed delivered.")]
    read_seq: Annotated[int, Field(ge=0, description="Last sequence marked as read by user.")]
    visible_from_seq: Annotated[
        int,
        Field(ge=1, description="Earliest sequence this user has permission to read."),
    ]


class SyncConversationsResponse(BaseModel):
    """List of all active conversation memberships and cursors for catch-up sync."""

    conversations: Annotated[
        list[ConversationSyncItem],
        Field(description="List of active conversation synchronization states."),
    ]


class MessageItem(BaseModel):
    """A single stored message in a conversation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
                "seq": 150,
                "id": "0192df78-8bc4-7123-93df-520e5e4860b0",
                "sender_id": "f4d5e6f7-a8b9-8091-a2b3-c4d5e6f7a8d1",
                "client_msg_id": "b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e",
                "kind": "text",
                "target_seq": None,
                "body": "All services healthy on Postgres 18 and Valkey.",
                "attachment_id": None,
                "enc_scheme": 0,
                "created_at": "2026-10-30T10:15:30.123456Z",
            }
        }
    )

    conversation_id: Annotated[UUID, Field(description="ID of the conversation.")]
    seq: Annotated[int, Field(ge=1, description="Message sequence number in this chat.")]
    id: Annotated[UUID, Field(description="Message UUIDv7.")]
    sender_id: Annotated[UUID, Field(description="User ID of the sender.")]
    client_msg_id: Annotated[UUID, Field(description="Client-provided idempotency ID.")]
    kind: Annotated[
        Literal["text", "media", "system", "delete", "edit"],
        Field(description="Kind of message."),
    ]
    target_seq: Annotated[
        int | None,
        Field(default=None, description="Target sequence if kind is 'delete' or 'edit'."),
    ]
    body: Annotated[str | None, Field(default=None, description="Message body text.")]
    attachment_id: Annotated[
        UUID | None,
        Field(default=None, description="Associated media attachment ID if any."),
    ]
    enc_scheme: Annotated[int, Field(default=0, description="Encryption scheme.")]
    created_at: Annotated[datetime, Field(description="Message creation timestamp.")]


class GetMessagesResponse(BaseModel):
    """Paginated messages response for catch-up and conversation viewing."""

    messages: Annotated[list[MessageItem], Field(description="List of messages in order of seq.")]
    has_more: Annotated[
        bool,
        Field(description="True if there are additional newer messages to fetch."),
    ]
    last_seq: Annotated[int, Field(ge=0, description="Highest sequence returned in this batch.")]


class DeleteMessageResponse(BaseModel):
    """Response returned upon successfully creating a tombstone message deletion (P2)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "seq": 155,
                "id": "0192df78-8bc4-7123-93df-520e5e4860f5",
                "target_seq": 150,
                "kind": "delete",
                "created_at": "2026-10-30T10:20:00.000000Z",
            }
        }
    )

    seq: Annotated[int, Field(ge=1, description="Sequence number of the tombstone entry.")]
    id: Annotated[UUID, Field(description="UUIDv7 of the tombstone message.")]
    target_seq: Annotated[int, Field(ge=1, description="Sequence number of the deleted message.")]
    kind: Annotated[Literal["delete"], Field(default="delete", description="Tombstone kind.")]
    created_at: Annotated[datetime, Field(description="Timestamp when deletion was recorded.")]

