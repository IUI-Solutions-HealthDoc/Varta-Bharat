"""Who gets a push for a message, and delivery to their devices."""

import logging
from uuid import UUID

import psycopg

from app.push.payload import build_payload
from app.push.senders import Sender

log = logging.getLogger("varta")

PUSH_KINDS = ("text", "media")  # never push deletes, edits or system messages

RECIPIENT_DEVICES = """
SELECT d.id, d.platform, d.push_token
FROM conversation_members cm
JOIN users u ON u.id = cm.user_id AND u.status = 'active'
JOIN tenant_members tm ON tm.user_id = cm.user_id AND tm.tenant_id = %s
  AND tm.removed_at IS NULL
JOIN devices d ON d.user_id = cm.user_id AND d.revoked_at IS NULL
  AND d.push_token IS NOT NULL
WHERE cm.conversation_id = %s
  AND cm.left_at IS NULL
  AND cm.user_id <> %s
  AND (cm.muted_until IS NULL OR cm.muted_until <= now())
  AND cm.visible_from_seq <= %s
  AND cm.delivered_seq < %s
  AND NOT EXISTS (
    SELECT 1 FROM user_blocks b WHERE b.blocker_id = cm.user_id AND b.blocked_id = %s)
"""


def deliver_push(
    conn: psycopg.Connection, sender: Sender, conversation_id: UUID, seq: int
) -> dict:
    """Send an ID-only push for message (conversation_id, seq) to members' devices."""
    result = {"sent": 0, "dead": 0, "failed": 0}
    msg = conn.execute(
        "SELECT m.kind, m.sender_id, c.tenant_id FROM messages m "
        "JOIN conversations c ON c.id = m.conversation_id "
        "WHERE m.conversation_id = %s AND m.seq = %s",
        (conversation_id, seq),
    ).fetchone()
    if msg is None or msg[0] not in PUSH_KINDS:
        return result
    _, sender_id, tenant_id = msg
    devices = conn.execute(
        RECIPIENT_DEVICES, (tenant_id, conversation_id, sender_id, seq, seq, sender_id)
    ).fetchall()
    payload = build_payload(tenant_id, conversation_id, seq)
    for device_id, platform, token in devices:
        try:
            outcome = sender.send(platform, token, payload)
        except Exception as exc:  # noqa: BLE001  one bad device must not stop the rest
            log.warning("push send failed", extra={"ctx": {"error": type(exc).__name__}})
            result["failed"] += 1
            continue
        if outcome == "ok":
            result["sent"] += 1
        elif outcome == "dead":
            conn.execute(
                "UPDATE devices SET push_token = NULL WHERE id = %s AND push_token = %s",
                (device_id, token),
            )
            result["dead"] += 1
        else:
            result["failed"] += 1
    return result