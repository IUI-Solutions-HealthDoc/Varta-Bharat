"""Send path, plan v2 section 7.2 (BE-1: Hardened P1 implementation).

One transaction: lock the conversation row by bumping last_seq, detect retries, check
permissions (including blocks and attachments), insert. A retry rolls back, which also
undoes the last_seq bump, so seq stays gapless (invariant I3). Never use INSERT ... ON CONFLICT DO NOTHING here.
After commit, publishes realtime hint to Valkey and enqueues push notifications.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import json
import logging
import unicodedata
from uuid import UUID

import psycopg
from psycopg.pq import TransactionStatus

log = logging.getLogger("varta.send")


class NotAllowed(Exception):
    """Sender may not post in this conversation."""


@dataclass(frozen=True)
class Sent:
    seq: int
    id: UUID
    created_at: datetime
    duplicate: bool = False


class _Duplicate(Exception):
    def __init__(self, row: tuple):
        self.row = row


def validate_attachment_for_send(
    conn: psycopg.Connection,
    attachment_id: UUID,
    sender_id: UUID,
    tenant_id: UUID,
) -> None:
    """Member 3 attachment hook: validates that attachment is ready, in same tenant, and owned by sender."""
    row = conn.execute(
        "SELECT state, tenant_id, uploader_id FROM attachments WHERE id = %s",
        (attachment_id,),
    ).fetchone()
    if row is None:
        raise NotAllowed("attachment not found")
    state, att_tenant, uploader = row
    if state != "ready":
        raise NotAllowed("attachment is not ready")
    if att_tenant != tenant_id:
        raise NotAllowed("attachment belongs to another tenant")
    if uploader != sender_id:
        raise NotAllowed("attachment was uploaded by another user")


def publish_hint(
    conversation_id: UUID,
    seq: int,
    message_id: UUID,
    sender_id: UUID,
    kind: str,
    created_at: datetime,
    body: str | None = None,
    attachment_id: UUID | None = None,
) -> None:
    """Publish realtime message hint to Valkey channel for WebSocket gateway subscribers."""
    try:
        from app.config import settings
        import valkey

        url = settings.valkey_url
        if url.startswith("redis://"):
            url = "valkey://" + url.removeprefix("redis://")
        client = valkey.Valkey.from_url(url, decode_responses=True)

        payload = {
            "conversation_id": str(conversation_id),
            "seq": seq,
            "id": str(message_id),
            "sender_id": str(sender_id),
            "kind": kind,
            "created_at": created_at.isoformat(),
        }
        # If payload body is <= 4096 bytes, include full body in hint payload
        body_bytes = body.encode("utf-8") if body else b""
        if len(body_bytes) <= 4096:
            payload["body"] = body
            payload["attachment_id"] = str(attachment_id) if attachment_id else None

        channel = f"conv:{conversation_id}"
        client.publish(channel, json.dumps(payload))
    except Exception as exc:  # noqa: BLE001
        # Post-commit Valkey glitch must not fail an already-committed message transaction
        log.warning("publish_hint failed: %s", exc)

    try:
        from app.ws.router import broadcast_realtime_message

        broadcast_realtime_message(
            conversation_id=conversation_id,
            seq=seq,
            message_id=message_id,
            sender_id=sender_id,
            kind=kind,
            created_at=created_at,
            body=body,
            attachment_id=attachment_id,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug("broadcast_realtime_message error: %s", exc)


def enqueue_push(conversation_id: UUID, seq: int) -> None:
    """Member 3 push notification hook: enqueue ID-only push notification for offline members."""
    try:
        from app.push import enqueue_push as push_hook

        push_hook(conversation_id, seq)
    except (ImportError, AttributeError):
        pass
    except Exception as exc:  # noqa: BLE001
        log.warning("enqueue_push failed: %s", exc)


def send_message(
    conn: psycopg.Connection,
    *,
    conversation_id: UUID,
    sender_id: UUID,
    client_msg_id: UUID,
    kind: str = "text",
    body: str | None = None,
    attachment_id: UUID | None = None,
    attachment_validator: Callable[
        [psycopg.Connection, UUID, UUID, UUID], None
    ] = validate_attachment_for_send,
) -> Sent:
    """Hardened send_message transaction.

    Enforces:
    - Never called in an outer transaction (must be IDLE).
    - Client kinds must be 'text' or 'media'.
    - Body length max 8000 characters.
    - Unicode NFC normalization.
    - Active membership & tenant check.
    - Announcement channel admin check.
    - User blocks check (sender/recipient in DMs).
    - Attachment readiness, tenant, and uploader check.
    - Gapless monotonic sequence assignment with idempotent duplicate detection.
    - Post-commit Valkey hint & push enqueuing.
    """
    # 0. Invariant safety: never run inside an open transaction
    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise RuntimeError("send_message must not be called inside an open transaction")

    # 1. Input validations
    if kind not in ("text", "media"):
        raise NotAllowed(f"Clients may only send 'text' or 'media', not '{kind}'")

    if body is not None:
        if len(body) > 8000:
            raise ValueError("Message body exceeds 8000 characters limit.")
        body = unicodedata.normalize("NFC", body)
    elif kind == "text":
        raise ValueError("Text messages must include a body.")

    if kind == "media" and attachment_id is None:
        raise ValueError("Media messages must include an attachment_id.")

    try:
        with conn.transaction():
            # Step 1: Serialise sends per conversation and take the next seq.
            row = conn.execute(
                "UPDATE conversations SET last_seq = last_seq + 1 "
                "WHERE id = %s RETURNING last_seq, kind, tenant_id",
                (conversation_id,),
            ).fetchone()
            if row is None:
                raise NotAllowed("conversation not found")
            seq, conv_kind, tenant_id = row

            # Step 2: Retry of an earlier send? Return the original; the rollback undoes step 1.
            dup = conn.execute(
                "SELECT seq, id, created_at FROM messages "
                "WHERE conversation_id = %s AND sender_id = %s AND client_msg_id = %s",
                (conversation_id, sender_id, client_msg_id),
            ).fetchone()
            if dup is not None:
                raise _Duplicate(dup)

            # Step 3: Permission checks
            # 3a. Active tenant & conversation membership
            member = conn.execute(
                "SELECT cm.role FROM conversation_members cm "
                "JOIN tenant_members tm ON tm.user_id = cm.user_id AND tm.tenant_id = %s "
                "JOIN users u ON u.id = cm.user_id "
                "WHERE cm.conversation_id = %s AND cm.user_id = %s "
                "AND cm.left_at IS NULL AND tm.removed_at IS NULL AND u.status = 'active'",
                (tenant_id, conversation_id, sender_id),
            ).fetchone()
            if member is None:
                raise NotAllowed("not an active member")

            # 3b. Announcement channel restriction
            if conv_kind == "announcement" and member[0] != "admin":
                raise NotAllowed("only admins can post in announcement channels")

            # 3c. User block check (for DMs, neither party may be blocked by the other)
            if conv_kind == "dm":
                other = conn.execute(
                    "SELECT user_id FROM conversation_members "
                    "WHERE conversation_id = %s AND user_id <> %s",
                    (conversation_id, sender_id),
                ).fetchone()
                if other is not None:
                    other_id = other[0]
                    blocked = conn.execute(
                        "SELECT 1 FROM user_blocks "
                        "WHERE (blocker_id = %s AND blocked_id = %s) "
                        "   OR (blocker_id = %s AND blocked_id = %s)",
                        (sender_id, other_id, other_id, sender_id),
                    ).fetchone()
                    if blocked is not None:
                        raise NotAllowed("user is blocked")

            # 3d. Attachment validation
            if attachment_id is not None:
                attachment_validator(conn, attachment_id, sender_id, tenant_id)

            # Step 4: Insert the message
            inserted = conn.execute(
                "INSERT INTO messages "
                "(conversation_id, seq, sender_id, client_msg_id, kind, body, attachment_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING seq, id, created_at",
                (conversation_id, seq, sender_id, client_msg_id, kind, body, attachment_id),
            ).fetchone()
    except _Duplicate as dup_exc:
        s, mid, created = dup_exc.row
        return Sent(seq=s, id=mid, created_at=created, duplicate=True)

    msg_seq, msg_id, created_at = inserted[0], inserted[1], inserted[2]

    # Step 5: After commit hooks (Valkey pub/sub and push enqueue)
    publish_hint(
        conversation_id=conversation_id,
        seq=msg_seq,
        message_id=msg_id,
        sender_id=sender_id,
        kind=kind,
        created_at=created_at,
        body=body,
        attachment_id=attachment_id,
    )
    enqueue_push(conversation_id, msg_seq)

    return Sent(seq=msg_seq, id=msg_id, created_at=created_at, duplicate=False)
