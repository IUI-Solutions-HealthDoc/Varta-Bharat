"""Send path, plan v2 section 7.2.

One transaction: lock the conversation row by bumping last_seq, detect retries, check
permissions, insert. A retry rolls back, which also undoes the last_seq bump, so seq stays
gapless (invariant I3). Never use INSERT ... ON CONFLICT DO NOTHING here.
"""

import unicodedata
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import psycopg


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


def send_message(
    conn: psycopg.Connection,
    *,
    conversation_id: UUID,
    sender_id: UUID,
    client_msg_id: UUID,
    kind: str = "text",
    body: str | None = None,
    attachment_id: UUID | None = None,
) -> Sent:
    if body is not None:
        body = unicodedata.normalize("NFC", body)
    try:
        with conn.transaction():
            # 1. Serialise sends per conversation and take the next seq.
            row = conn.execute(
                "UPDATE conversations SET last_seq = last_seq + 1 "
                "WHERE id = %s RETURNING last_seq, kind, tenant_id",
                (conversation_id,),
            ).fetchone()
            if row is None:
                raise NotAllowed("conversation not found")
            seq, conv_kind, tenant_id = row

            # 2. Retry of an earlier send? Return the original; the rollback undoes step 1.
            dup = conn.execute(
                "SELECT seq, id, created_at FROM messages "
                "WHERE conversation_id = %s AND sender_id = %s AND client_msg_id = %s",
                (conversation_id, sender_id, client_msg_id),
            ).fetchone()
            if dup is not None:
                raise _Duplicate(dup)

            # 3. Permission checks, then insert.
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
            if conv_kind == "announcement" and member[0] != "admin":
                raise NotAllowed("only admins can post in announcement channels")

            inserted = conn.execute(
                "INSERT INTO messages "
                "(conversation_id, seq, sender_id, client_msg_id, kind, body, attachment_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING seq, id, created_at",
                (conversation_id, seq, sender_id, client_msg_id, kind, body, attachment_id),
            ).fetchone()
    except _Duplicate as dup_exc:
        s, mid, created = dup_exc.row
        return Sent(seq=s, id=mid, created_at=created, duplicate=True)

    # 4. After commit (not implemented yet): publish {conv, seq} to Valkey, enqueue push.
    return Sent(seq=inserted[0], id=inserted[1], created_at=inserted[2])
