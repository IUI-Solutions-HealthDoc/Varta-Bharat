from uuid import uuid4

from app.media.tasks import sweep_pending
from app.worker import celery_app
from tests.helpers import seed_chat


class Store:
    def __init__(self):
        self.keys = set()
        self.deleted = []

    def object_size(self, key):
        return 10 if key in self.keys else None

    def delete(self, key):
        self.deleted.append(key)


def make(conn, chat, store, age_s, uploaded=True, state="pending"):
    key = f"{chat['tenant']}/{uuid4()}"
    att = conn.execute(
        "INSERT INTO attachments (tenant_id, uploader_id, object_key, mime, byte_size, state, "
        "created_at) VALUES (%s, %s, %s, 'image/png', 1000, %s, "
        "now() - make_interval(secs => %s)) RETURNING id",
        (chat["tenant"], chat["alice"], key, state, age_s),
    ).fetchone()[0]
    if uploaded:
        store.keys.add(key)
    return att, key


def state_of(conn, att):
    return conn.execute("SELECT state FROM attachments WHERE id = %s", (att,)).fetchone()[0]


def test_stale_uploaded_attachment_is_requeued(conn):
    chat, store, queued = seed_chat(conn), Store(), []
    att, _ = make(conn, chat, store, age_s=600)
    result = sweep_pending(conn, store, queued.append)
    assert result == {"expired": 0, "requeued": 1}
    assert queued == [att]
    assert state_of(conn, att) == "pending"


def test_stale_without_upload_is_left_alone(conn):
    chat, store, queued = seed_chat(conn), Store(), []
    make(conn, chat, store, age_s=600, uploaded=False)
    assert sweep_pending(conn, store, queued.append) == {"expired": 0, "requeued": 0}
    assert queued == []


def test_fresh_attachment_is_left_alone(conn):
    chat, store, queued = seed_chat(conn), Store(), []
    make(conn, chat, store, age_s=30)
    assert sweep_pending(conn, store, queued.append) == {"expired": 0, "requeued": 0}
    assert queued == []


def test_day_old_pending_is_rejected_and_objects_deleted(conn):
    chat, store, queued = seed_chat(conn), Store(), []
    att, key = make(conn, chat, store, age_s=25 * 3600)
    assert sweep_pending(conn, store, queued.append) == {"expired": 1, "requeued": 0}
    assert state_of(conn, att) == "rejected"
    assert store.deleted == [key, f"{key}.thumb"]
    assert queued == []


def test_ready_and_rejected_rows_are_never_touched(conn):
    chat, store, queued = seed_chat(conn), Store(), []
    ready, _ = make(conn, chat, store, age_s=3 * 86400, state="ready")
    rejected, _ = make(conn, chat, store, age_s=3 * 86400, state="rejected")
    assert sweep_pending(conn, store, queued.append) == {"expired": 0, "requeued": 0}
    assert state_of(conn, ready) == "ready"
    assert state_of(conn, rejected) == "rejected"
    assert store.deleted == []


def test_batch_limit_bounds_one_run(conn):
    chat, store, queued = seed_chat(conn), Store(), []
    for _ in range(3):
        make(conn, chat, store, age_s=600)
    assert sweep_pending(conn, store, queued.append, batch=2)["requeued"] == 2


def test_sweep_is_scheduled_every_minute():
    entry = celery_app.conf.beat_schedule["sweep-pending-attachments"]
    assert entry["task"] == "app.media.tasks.sweep_pending_attachments"
    assert entry["schedule"] == 60.0