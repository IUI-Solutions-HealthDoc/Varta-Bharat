"""Pydantic schemas for Varta Bharat WebSocket Gateway frames (BE-1).

Defines upstream (client -> server) and downstream (server -> client) frames
as described in docs/protocol.md and Plan v2 section 7.3.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HelloFrame(BaseModel):
    """Initial client frame containing authentication ticket."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"type": "hello", "ticket": "wstk_8f91a2c3d4e5f67890abcdef"}}
    )

    type: Annotated[Literal["hello"], Field(default="hello")]
    ticket: Annotated[
        str,
        Field(description="Single-use, 30s ticket issued by POST /v1/ws-ticket."),
    ]


class AckFrame(BaseModel):
    """Client frame advancing delivered and read sequence cursors."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "ack",
                "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
                "delivered_seq": 150,
                "read_seq": 145,
            }
        }
    )

    type: Annotated[Literal["ack"], Field(default="ack")]
    conversation_id: Annotated[UUID, Field(description="Conversation ID for the acknowledgment.")]
    delivered_seq: Annotated[
        int,
        Field(ge=0, description="Highest sequence number delivered to client."),
    ]
    read_seq: Annotated[int, Field(ge=0, description="Highest sequence number read by client.")]


class TypingFrame(BaseModel):
    """Client/Server frame indicating typing activity (P2)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "typing",
                "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
                "user_id": "0192df78-0000-7000-8000-000000000001",
                "is_typing": True,
            }
        }
    )

    type: Annotated[Literal["typing"], Field(default="typing")]
    conversation_id: Annotated[UUID, Field(description="Conversation where typing is occurring.")]
    user_id: Annotated[
        UUID | None,
        Field(default=None, description="User who is typing (populated by server in broadcast)."),
    ]
    is_typing: Annotated[bool, Field(description="True if typing, False when typing stops.")]


class WelcomeFrame(BaseModel):
    """Server frame welcoming client upon successful ticket validation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "welcome",
                "heartbeat_s": 25,
                "user_id": "e3c4d5e6-f7a8-8091-a2b3-c4d5e6f7a8c0",
                "device_id": "0192df70-1234-7abc-8def-000000000001",
            }
        }
    )

    type: Annotated[Literal["welcome"], Field(default="welcome")]
    heartbeat_s: Annotated[int, Field(default=25, description="Heartbeat ping interval in seconds.")]
    user_id: Annotated[UUID, Field(description="Authenticated user UUID.")]
    device_id: Annotated[UUID, Field(description="Registered device UUID.")]


class MsgFrame(BaseModel):
    """Server frame delivering full message (<= 4 KB) to online clients."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "msg",
                "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
                "seq": 151,
                "id": "0192df78-8bc4-7123-93df-520e5e4860c2",
                "sender_id": "e3c4d5e6-f7a8-8091-a2b3-c4d5e6f7a8c0",
                "kind": "text",
                "body": "Realtime notification received!",
                "attachment_id": None,
                "created_at": "2026-10-30T10:16:00.000000Z",
            }
        }
    )

    type: Annotated[Literal["msg"], Field(default="msg")]
    conversation_id: Annotated[UUID, Field(description="Conversation ID.")]
    seq: Annotated[int, Field(ge=1, description="Message sequence number.")]
    id: Annotated[UUID, Field(description="Message UUIDv7.")]
    sender_id: Annotated[UUID, Field(description="Sender user UUID.")]
    kind: Annotated[str, Field(description="Message kind (text, media, etc.).")]
    body: Annotated[str | None, Field(default=None, description="Message body text.")]
    attachment_id: Annotated[UUID | None, Field(default=None, description="Attachment ID.")]
    created_at: Annotated[datetime, Field(description="Creation timestamp.")]


class MsgHintFrame(BaseModel):
    """Server frame delivering lightweight hint for large messages (> 4 KB)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "msg_hint",
                "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
                "seq": 152,
                "id": "0192df78-8bc4-7123-93df-520e5e4860d3",
                "sender_id": "e3c4d5e6-f7a8-8091-a2b3-c4d5e6f7a8c0",
                "kind": "media",
                "created_at": "2026-10-30T10:16:30.000000Z",
            }
        }
    )

    type: Annotated[Literal["msg_hint"], Field(default="msg_hint")]
    conversation_id: Annotated[UUID, Field(description="Conversation ID.")]
    seq: Annotated[int, Field(ge=1, description="Message sequence number.")]
    id: Annotated[UUID, Field(description="Message UUIDv7.")]
    sender_id: Annotated[UUID, Field(description="Sender user UUID.")]
    kind: Annotated[str, Field(description="Message kind.")]
    created_at: Annotated[datetime, Field(description="Creation timestamp.")]


class ReceiptFrame(BaseModel):
    """Server frame informing participants of updated delivery/read cursors."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "receipt",
                "conversation_id": "c1a2b3c4-d5e6-7f80-91a2-b3c4d5e6f7a8",
                "user_id": "f4d5e6f7-a8b9-8091-a2b3-c4d5e6f7a8d1",
                "delivered_seq": 151,
                "read_seq": 151,
            }
        }
    )

    type: Annotated[Literal["receipt"], Field(default="receipt")]
    conversation_id: Annotated[UUID, Field(description="Conversation ID.")]
    user_id: Annotated[UUID, Field(description="User advancing their cursors.")]
    delivered_seq: Annotated[int, Field(ge=0, description="Highest delivered sequence.")]
    read_seq: Annotated[int, Field(ge=0, description="Highest read sequence.")]


class RevokedFrame(BaseModel):
    """Server frame notifying device of immediate session revocation (P2)."""

    type: Annotated[Literal["revoked"], Field(default="revoked")]
    reason: Annotated[str, Field(description="Reason for revocation.")]


class ErrorFrame(BaseModel):
    """Server frame indicating protocol or authentication error."""

    type: Annotated[Literal["error"], Field(default="error")]
    code: Annotated[str, Field(description="Machine-readable error code.")]
    message: Annotated[str, Field(description="Human-readable description of error.")]
