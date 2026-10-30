import base64
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core import db
from app.main import app
from app.media.storage import MAX_UPLOAD_BYTES, Storage, get_storage
from tests.helpers import seed_chat


class FakeStorage:
    def __init__(self):
        self.sizes = {}

    def presign_post(self, key, mime):
        return {"url": "http://s3.test/varta-media", "fields": {"key": key, "Content-Type": mime}}

    def object_size(self, key):
        return self.sizes.get(key)


@pytest.fixture
def client(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)
    db.close_pool()
    storage = FakeStorage()
    app.dependency_overrides[get_storage] = lambda: storage
    monkeypatch.setattr("app.media.router.enqueue_processing", lambda attachment_id: None)
    with TestClient(app) as c:
        c.storage = storage
        yield c
    app.dependency_overrides.clear()
    db.close_pool()


def hdr(chat, who="alice", tenant=None):
    return {
        "X-Dev-User-Id": str(chat[who]),
        "X-Dev-Tenant-Id": str(tenant or chat["tenant"]),
    }


def create(client, chat, who="alice", mime="image/png", size=1000):
    return client.post(
        "/v1/attachments", json={"mime": mime, "byte_size": size}, headers=hdr(chat, who)
    )


def test_create_returns_presigned_post_and_pending_row(client, conn):
    chat = seed_chat(conn)
    r = create(client, chat)
    assert r.status_code == 201
    body = r.json()
    row = conn.execute(
        "SELECT object_key, state, uploader_id, tenant_id FROM attachments WHERE id = %s",
        (UUID(body["id"]),),
    ).fetchone()
    assert row[1] == "pending"
    assert row[2] == chat["alice"]
    assert row[3] == chat["tenant"]
    assert row[0].startswith(f"{chat['tenant']}/")
    assert body["fields"]["key"] == row[0]


@pytest.mark.parametrize(
    "payload",
    [
        {"mime": "image/png", "byte_size": 0},
        {"mime": "image/png", "byte_size": MAX_UPLOAD_BYTES + 1},
        {"mime": "application/x-msdownload", "byte_size": 100},
    ],
)
def test_create_validates_input(client, conn, payload):
    chat = seed_chat(conn)
    r = client.post("/v1/attachments", json=payload, headers=hdr(chat))
    assert r.status_code == 422


def test_requires_auth(client):
    r = client.post("/v1/attachments", json={"mime": "image/png", "byte_size": 10})
    assert r.status_code == 401


def test_complete_without_upload_is_409(client, conn):
    chat = seed_chat(conn)
    att = create(client, chat).json()["id"]
    r = client.post(f"/v1/attachments/{att}/complete", headers=hdr(chat))
    assert r.status_code == 409


def test_complete_after_upload_records_real_size_and_stays_pending(client, conn):
    chat = seed_chat(conn)
    body = create(client, chat).json()
    client.storage.sizes[body["fields"]["key"]] = 5000
    r = client.post(f"/v1/attachments/{body['id']}/complete", headers=hdr(chat))
    assert r.status_code == 200
    assert r.json()["state"] == "pending"
    size = conn.execute(
        "SELECT byte_size FROM attachments WHERE id = %s", (UUID(body["id"]),)
    ).fetchone()[0]
    assert size == 5000


def test_other_user_and_other_tenant_get_404(client, conn):
    chat = seed_chat(conn)
    att = create(client, chat).json()["id"]
    assert client.post(f"/v1/attachments/{att}/complete", headers=hdr(chat, "bob")).status_code == 404
    other = hdr(chat, tenant=uuid4())
    assert client.post(f"/v1/attachments/{att}/complete", headers=other).status_code == 404
    assert client.post(f"/v1/attachments/{uuid4()}/complete", headers=hdr(chat)).status_code == 404


def test_real_presigned_post_enforces_size_limit():
    post = Storage().presign_post("t/k", "image/png")
    policy = json.loads(base64.b64decode(post["fields"]["policy"]))
    assert ["content-length-range", 1, MAX_UPLOAD_BYTES] in policy["conditions"]
    assert {"Content-Type": "image/png"} in policy["conditions"]