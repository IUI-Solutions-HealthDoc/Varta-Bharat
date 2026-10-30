from uuid import uuid4

import pytest

from app.media.validation import AttachmentRejected, validate_attachment_for_send
from tests.helpers import seed_chat


def _attachment(conn, chat, uploader, state="ready"):
    return conn.execute(
        "INSERT INTO attachments (tenant_id, uploader_id, object_key, mime, byte_size, state) "
        "VALUES (%s, %s, %s, 'image/png', 1000, %s) RETURNING id",
        (chat["tenant"], uploader, f"k/{uuid4()}", state),
    ).fetchone()[0]


def test_ready_own_attachment_is_accepted(conn):
    chat = seed_chat(conn)
    att = _attachment(conn, chat, chat["alice"])
    validate_attachment_for_send(conn, att, chat["alice"], chat["tenant"])


@pytest.mark.parametrize("state", ["pending", "rejected"])
def test_not_ready_is_rejected(conn, state):
    chat = seed_chat(conn)
    att = _attachment(conn, chat, chat["alice"], state)
    with pytest.raises(AttachmentRejected, match=state):
        validate_attachment_for_send(conn, att, chat["alice"], chat["tenant"])


def test_other_users_attachment_is_rejected(conn):
    chat = seed_chat(conn)
    att = _attachment(conn, chat, chat["alice"])
    with pytest.raises(AttachmentRejected, match="another user"):
        validate_attachment_for_send(conn, att, chat["bob"], chat["tenant"])


def test_other_tenant_is_rejected(conn):
    chat = seed_chat(conn)
    att = _attachment(conn, chat, chat["alice"])
    with pytest.raises(AttachmentRejected, match="not found"):
        validate_attachment_for_send(conn, att, chat["alice"], uuid4())


def test_unknown_id_is_rejected(conn):
    chat = seed_chat(conn)
    with pytest.raises(AttachmentRejected, match="not found"):
        validate_attachment_for_send(conn, uuid4(), chat["alice"], chat["tenant"])
