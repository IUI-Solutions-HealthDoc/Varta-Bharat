import io
from uuid import uuid4

import pytest
from PIL import Image

from app.media.processing import process_attachment
from tests.helpers import seed_chat


class FakeStorage:
    def __init__(self):
        self.objects = {}
        self.deleted = []

    def get_bytes(self, key, limit):
        data = self.objects.get(key)
        return None if data is None else data[: limit + 1]

    def put_bytes(self, key, data, content_type):
        self.objects[key] = data

    def delete(self, key):
        self.deleted.append(key)
        self.objects.pop(key, None)


def image_bytes(fmt="PNG", size=(800, 400)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, fmt)
    return buf.getvalue()


def make(conn, chat, storage, data, mime):
    key = f"{chat['tenant']}/{uuid4()}"
    att = conn.execute(
        "INSERT INTO attachments (tenant_id, uploader_id, object_key, mime, byte_size) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (chat["tenant"], chat["alice"], key, mime, len(data) if data else 1000),
    ).fetchone()[0]
    if data is not None:
        storage.objects[key] = data
    return att, key


def row(conn, att):
    return conn.execute(
        "SELECT state, width, height, sha256 FROM attachments WHERE id = %s", (att,)
    ).fetchone()


def test_valid_png_becomes_ready_with_thumbnail(conn):
    chat, storage = seed_chat(conn), FakeStorage()
    att, key = make(conn, chat, storage, image_bytes(), "image/png")
    assert process_attachment(conn, storage, att) == "ready"
    state, width, height, sha = row(conn, att)
    assert (state, width, height) == ("ready", 800, 400)
    assert sha is not None and len(sha) == 32
    thumb = Image.open(io.BytesIO(storage.objects[f"{key}.thumb"]))
    assert max(thumb.size) <= 320


def test_pdf_becomes_ready_without_thumbnail(conn):
    chat, storage = seed_chat(conn), FakeStorage()
    att, key = make(conn, chat, storage, b"%PDF-1.4\n%test\n1 0 obj\n<<>>\nendobj\n", "application/pdf")
    assert process_attachment(conn, storage, att) == "ready"
    assert f"{key}.thumb" not in storage.objects


def test_text_declared_as_png_is_rejected_and_deleted(conn):
    chat, storage = seed_chat(conn), FakeStorage()
    att, key = make(conn, chat, storage, b"just some text, not an image", "image/png")
    assert process_attachment(conn, storage, att) == "rejected"
    assert row(conn, att)[0] == "rejected"
    assert key in storage.deleted


def test_type_mismatch_is_rejected(conn):
    chat, storage = seed_chat(conn), FakeStorage()
    att, _ = make(conn, chat, storage, image_bytes("JPEG"), "image/png")
    assert process_attachment(conn, storage, att) == "rejected"


def test_missing_upload_stays_pending(conn):
    chat, storage = seed_chat(conn), FakeStorage()
    att, _ = make(conn, chat, storage, None, "image/png")
    assert process_attachment(conn, storage, att) == "pending"
    assert row(conn, att)[0] == "pending"


def test_already_processed_is_not_reprocessed(conn):
    chat, storage = seed_chat(conn), FakeStorage()
    att, _ = make(conn, chat, storage, image_bytes(), "image/png")
    assert process_attachment(conn, storage, att) == "ready"
    storage.objects.clear()
    assert process_attachment(conn, storage, att) == "ready"


def test_unknown_id_raises(conn):
    with pytest.raises(LookupError):
        process_attachment(conn, FakeStorage(), uuid4())