import types
from uuid import uuid4

import pytest

from app.config import settings
from app.core import db
from app.media import tasks
from app.media.tasks import process_attachment_task
from tests.helpers import seed_chat
from tests.test_attachment_processing import FakeStorage, image_bytes, make


@pytest.fixture
def pool(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)
    db.close_pool()
    yield
    db.close_pool()


def test_task_marks_attachment_ready(pool, conn, monkeypatch):
    chat, storage = seed_chat(conn), FakeStorage()
    att, _ = make(conn, chat, storage, image_bytes(), "image/png")
    conn.commit()  # the task uses its own connection
    monkeypatch.setattr(tasks, "get_storage", lambda: storage)
    assert process_attachment_task.apply(args=[str(att)]).get() == "ready"
    state = conn.execute("SELECT state FROM attachments WHERE id = %s", (att,)).fetchone()[0]
    assert state == "ready"


def test_enqueue_failure_does_not_raise(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("broker down")

    monkeypatch.setattr(tasks, "process_attachment_task", types.SimpleNamespace(delay=boom))
    tasks.enqueue_processing(uuid4())