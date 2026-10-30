"""Attachment checks used by the send path (called from send_message, inside its transaction)."""

from uuid import UUID

import psycopg


class AttachmentRejected(Exception):
    """The attachment cannot be used in this message. `reason` is safe to show clients."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def validate_attachment_for_send(
    conn: psycopg.Connection,
    attachment_id: UUID,
    sender_id: UUID,
    tenant_id: UUID,
) -> None:
    """Raise AttachmentRejected unless the attachment is ready, uploaded by the sender and
    belongs to the same tenant. Unknown id and other tenant's id give the same answer, so
    ids from other tenants cannot be probed."""
    row = conn.execute(
        "SELECT tenant_id, uploader_id, state FROM attachments WHERE id = %s",
        (attachment_id,),
    ).fetchone()
    if row is None or row[0] != tenant_id:
        raise AttachmentRejected("attachment not found")
    if row[1] != sender_id:
        raise AttachmentRejected("attachment belongs to another user")
    if row[2] != "ready":
        raise AttachmentRejected(f"attachment is {row[2]}")
