from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core import db
from app.main import app
from app.media.storage import get_storage
from tests.helpers import auth_headers, seed_chat


class FakeStorage:
    def presign_post(self, key, mime):
        return {"url": "http://s3.test/varta-media", "fields": {"key": key, "Content-Type": mime}}

    def object_size(self, key):
        return None


@pytest.fixture
def client(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)
    db.close_pool()
    monkeypatch.setattr("app.media.router.enqueue_processing", lambda attachment_id: None)
    app.dependency_overrides[get_storage] = lambda: FakeStorage()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    db.close_pool()


PAYLOAD = {"mime": "image/png", "byte_size": 1000}


def create(client, headers, key=None, payload=PAYLOAD):
    if key is not None:
        headers = {**headers, "X-Idempotency-Key": str(key)}
    return client.post("/v1/attachments", json=payload, headers=headers)


def count(conn, chat, who="alice"):
    return conn.execute(
        "SELECT count(*) FROM attachments WHERE uploader_id = %s", (chat[who],)
    ).fetchone()[0]


def test_retry_with_same_key_returns_the_same_attachment(client, conn):
    chat = seed_chat(conn)
    headers, key = auth_headers(chat), uuid4()
    first, second = create(client, headers, key), create(client, headers, key)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["fields"]["key"] == second.json()["fields"]["key"]
    assert count(conn, chat) == 1


@pytest.mark.parametrize(
    "other", [{"mime": "image/jpeg", "byte_size": 1000}, {"mime": "image/png", "byte_size": 2000}]
)
def test_same_key_with_a_different_upload_is_409(client, conn, other):
    chat = seed_chat(conn)
    headers, key = auth_headers(chat), uuid4()
    assert create(client, headers, key).status_code == 201
    assert create(client, headers, key, other).status_code == 409
    assert count(conn, chat) == 1


def test_without_a_key_nothing_is_deduplicated(client, conn):
    chat = seed_chat(conn)
    headers = auth_headers(chat)
    assert create(client, headers).json()["id"] != create(client, headers).json()["id"]
    assert count(conn, chat) == 2


def test_retry_after_rejection_creates_a_new_attachment(client, conn):
    chat = seed_chat(conn)
    headers, key = auth_headers(chat), uuid4()
    first = create(client, headers, key).json()["id"]
    conn.execute("UPDATE attachments SET state = 'rejected' WHERE id = %s", (first,))
    conn.commit()
    second = create(client, headers, key)
    assert second.status_code == 201
    assert second.json()["id"] != first
    assert count(conn, chat) == 2


def test_retry_after_the_object_was_checked_is_409(client, conn):
    chat = seed_chat(conn)
    headers, key = auth_headers(chat), uuid4()
    first = create(client, headers, key).json()["id"]
    conn.execute("UPDATE attachments SET state = 'ready' WHERE id = %s", (first,))
    conn.commit()
    assert create(client, headers, key).status_code == 409


def test_two_users_can_use_the_same_key(client, conn):
    chat, key = seed_chat(conn), uuid4()
    a = create(client, auth_headers(chat, "alice"), key)
    b = create(client, auth_headers(chat, "bob"), key)
    assert a.status_code == b.status_code == 201
    assert a.json()["id"] != b.json()["id"]


def test_malformed_key_is_422(client, conn):
    chat = seed_chat(conn)
    r = client.post(
        "/v1/attachments",
        json=PAYLOAD,
        headers={**auth_headers(chat), "X-Idempotency-Key": "not-a-uuid"},
    )
    assert r.status_code == 422


def test_idempotency_index_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'attachments_idempotency_key_uniq'"
    ).fetchone()
    assert row is not None