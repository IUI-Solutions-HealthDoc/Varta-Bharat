from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core import db
from app.main import app
from app.media.storage import get_storage
from tests.helpers import auth_headers, seed_chat


class FakeStorage:
    def presign_get(self, key, mime, disposition, seconds=300):
        return f"http://s3.test/{key}?type={mime}&disp={disposition}&exp={seconds}"


@pytest.fixture
def client(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)
    db.close_pool()
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    db.close_pool()


def attachment(conn, chat, uploader="alice", mime="image/png", state="ready"):
    row = conn.execute(
        "INSERT INTO attachments (tenant_id, uploader_id, object_key, mime, byte_size, state) "
        "VALUES (%s, %s, %s, %s, 1000, %s) RETURNING id, object_key",
        (chat["tenant"], chat[uploader], f"{chat['tenant']}/{uuid4()}", mime, state),
    ).fetchone()
    conn.commit()
    return row


def send_media(conn, chat, att_id, seq=1, sender="alice"):
    conn.execute(
        "UPDATE conversations SET last_seq = GREATEST(last_seq, %s) WHERE id = %s",
        (seq, chat["conv"]),
    )
    conn.execute(
        "INSERT INTO messages (conversation_id, seq, sender_id, client_msg_id, kind, attachment_id) "
        "VALUES (%s, %s, %s, %s, 'media', %s)",
        (chat["conv"], seq, chat[sender], uuid4(), att_id),
    )
    conn.commit()


def get(client, chat, att_id, who="bob", **params):
    return client.get(
        f"/v1/attachments/{att_id}/download", params=params, headers=auth_headers(chat, who)
    )


def test_member_gets_url_for_attachment_in_their_conversation(client, conn):
    chat = seed_chat(conn)
    att, key = attachment(conn, chat)
    send_media(conn, chat, att)
    r = get(client, chat, att)
    assert r.status_code == 200
    body = r.json()
    assert body["url"].startswith(f"http://s3.test/{key}?")
    assert body["mime"] == "image/png"
    assert body["expires_in"] == 300
    assert r.headers["cache-control"] == "no-store"


def test_uploader_can_download_before_sending(client, conn):
    chat = seed_chat(conn)
    att, _ = attachment(conn, chat)
    assert get(client, chat, att, "alice").status_code == 200


def test_tenant_member_outside_the_conversation_gets_404(client, conn):
    chat = seed_chat(conn)
    att, _ = attachment(conn, chat)
    send_media(conn, chat, att)
    assert get(client, chat, att, "carol").status_code == 404


def test_member_who_left_gets_404(client, conn):
    chat = seed_chat(conn)
    att, _ = attachment(conn, chat)
    send_media(conn, chat, att)
    conn.execute(
        "UPDATE conversation_members SET left_at = now() "
        "WHERE conversation_id = %s AND user_id = %s",
        (chat["conv"], chat["bob"]),
    )
    conn.commit()
    assert get(client, chat, att).status_code == 404


def test_message_before_visible_from_seq_is_hidden(client, conn):
    chat = seed_chat(conn)
    old, _ = attachment(conn, chat)
    new, _ = attachment(conn, chat)
    send_media(conn, chat, old, seq=1)
    send_media(conn, chat, new, seq=2)
    conn.execute(
        "UPDATE conversation_members SET visible_from_seq = 2 "
        "WHERE conversation_id = %s AND user_id = %s",
        (chat["conv"], chat["bob"]),
    )
    conn.commit()
    assert get(client, chat, old).status_code == 404
    assert get(client, chat, new).status_code == 200


def test_deleted_message_attachment_is_not_served_to_others(client, conn):
    chat = seed_chat(conn)
    att, _ = attachment(conn, chat)
    send_media(conn, chat, att, seq=1)
    conn.execute("UPDATE conversations SET last_seq = 2 WHERE id = %s", (chat["conv"],))
    conn.execute(
        "INSERT INTO messages (conversation_id, seq, sender_id, client_msg_id, kind, target_seq) "
        "VALUES (%s, 2, %s, %s, 'delete', 1)",
        (chat["conv"], chat["alice"], uuid4()),
    )
    conn.commit()
    assert get(client, chat, att, "bob").status_code == 404


@pytest.mark.parametrize("state", ["pending", "rejected"])
def test_only_ready_attachments_are_served(client, conn, state):
    chat = seed_chat(conn)
    att, _ = attachment(conn, chat, state=state)
    send_media(conn, chat, att)
    assert get(client, chat, att, "alice").status_code == 404
    assert get(client, chat, att, "bob").status_code == 404


def test_other_tenant_gets_404(client, conn):
    chat = seed_chat(conn)
    other = seed_chat(conn)
    att, _ = attachment(conn, chat)
    send_media(conn, chat, att)
    assert get(client, other, att, "alice").status_code == 404


def test_thumbnail_only_for_images(client, conn):
    chat = seed_chat(conn)
    img, key = attachment(conn, chat)
    pdf, _ = attachment(conn, chat, mime="application/pdf")
    send_media(conn, chat, img, seq=1)
    send_media(conn, chat, pdf, seq=2)
    r = get(client, chat, img, thumb="true")
    assert r.status_code == 200
    assert f"{key}.thumb?" in r.json()["url"]
    assert r.json()["mime"] == "image/jpeg"
    assert get(client, chat, pdf, thumb="true").status_code == 404


def test_pdf_is_served_as_attachment_not_inline(client, conn):
    chat = seed_chat(conn)
    pdf, _ = attachment(conn, chat, mime="application/pdf")
    send_media(conn, chat, pdf)
    assert "disp=attachment" in get(client, chat, pdf).json()["url"]


def test_requires_auth(client):
    assert client.get(f"/v1/attachments/{uuid4()}/download").status_code == 401