import types
from uuid import uuid4

from app.config import settings
from app.push import enqueue_push, tasks
from app.push.delivery import deliver_push
from tests.helpers import seed_chat


class FakeSender:
    def __init__(self, dead=()):
        self.calls = []
        self.dead = set(dead)

    def send(self, platform, token, payload):
        self.calls.append((platform, token, payload))
        return "dead" if token in self.dead else "ok"


def device(conn, user_id, token="tok", platform="android", revoked=False):
    conn.execute(
        "INSERT INTO devices (user_id, platform, push_token, refresh_hash, refresh_family) "
        "VALUES (%s, %s, %s, %s, %s)",
        (user_id, platform, token, b"hash", uuid4()),
    )
    if revoked:
        conn.execute("UPDATE devices SET revoked_at = now() WHERE push_token = %s", (token,))


def message(conn, chat, seq, sender="alice", kind="text", body="secret text", target_seq=None):
    conn.execute(
        "UPDATE conversations SET last_seq = GREATEST(last_seq, %s) WHERE id = %s",
        (seq, chat["conv"]),
    )
    conn.execute(
        "INSERT INTO messages (conversation_id, seq, sender_id, client_msg_id, kind, body, "
        "target_seq) VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (chat["conv"], seq, chat[sender], uuid4(), kind, body, target_seq),
    )


def member_update(conn, chat, who, assignment):
    conn.execute(
        f"UPDATE conversation_members SET {assignment} WHERE conversation_id = %s AND user_id = %s",
        (chat["conv"], chat[who]),
    )


def pushed_tokens(conn, chat, seq=1, sender=None):
    sender = sender or FakeSender()
    deliver_push(conn, sender, chat["conv"], seq)
    return [call[1] for call in sender.calls]


def test_the_hook_that_send_message_imports_exists():
    from app.push import enqueue_push as hook  # send.py swallows ImportError silently

    assert callable(hook)


def test_enqueue_is_a_noop_when_push_is_disabled(monkeypatch):
    def boom(**kwargs):
        raise AssertionError("must not queue")

    monkeypatch.setattr(settings, "push_provider", "none")
    monkeypatch.setattr(tasks, "push_task", types.SimpleNamespace(apply_async=boom))
    enqueue_push(uuid4(), 1)


def test_enqueue_queues_the_task_with_a_delay(monkeypatch):
    queued = []
    monkeypatch.setattr(settings, "push_provider", "fake")
    monkeypatch.setattr(settings, "push_delay_s", 7)
    monkeypatch.setattr(
        tasks,
        "push_task",
        types.SimpleNamespace(apply_async=lambda args, countdown: queued.append((args, countdown))),
    )
    conv = uuid4()
    enqueue_push(conv, 3)
    assert queued == [([str(conv), 3], 7)]


def test_enqueue_failure_does_not_raise(monkeypatch):
    def boom(**kwargs):
        raise ConnectionError("broker down")

    monkeypatch.setattr(settings, "push_provider", "fake")
    monkeypatch.setattr(tasks, "push_task", types.SimpleNamespace(apply_async=boom))
    enqueue_push(uuid4(), 1)


def test_member_devices_get_an_ids_only_push(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"], "bob-token")
    device(conn, chat["alice"], "alice-token")  # the sender
    device(conn, chat["carol"], "carol-token")  # in the tenant, not in the conversation
    sender = FakeSender()
    result = deliver_push(conn, sender, chat["conv"], 1)
    assert result == {"sent": 1, "dead": 0, "failed": 0}
    [(platform, token, payload)] = sender.calls
    assert (platform, token) == ("android", "bob-token")
    assert payload == {
        "tenant_id": str(chat["tenant"]),
        "conversation_id": str(chat["conv"]),
        "seq": "1",
    }
    assert "secret text" not in str(payload)


def test_missing_message_sends_nothing(conn):
    chat = seed_chat(conn)
    device(conn, chat["bob"])
    assert pushed_tokens(conn, chat, seq=5) == []


def test_deletes_are_not_pushed(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    message(conn, chat, 2, kind="delete", body=None, target_seq=1)
    device(conn, chat["bob"])
    assert pushed_tokens(conn, chat, seq=2) == []


def test_muted_member_is_skipped(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"])
    member_update(conn, chat, "bob", "muted_until = now() + interval '1 hour'")
    assert pushed_tokens(conn, chat) == []


def test_member_who_left_is_skipped(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"])
    member_update(conn, chat, "bob", "left_at = now()")
    assert pushed_tokens(conn, chat) == []


def test_message_before_visible_from_seq_is_skipped(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"])
    member_update(conn, chat, "bob", "visible_from_seq = 2")
    assert pushed_tokens(conn, chat) == []


def test_already_delivered_message_is_skipped(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"])
    member_update(conn, chat, "bob", "delivered_seq = 1")
    assert pushed_tokens(conn, chat) == []


def test_revoked_and_tokenless_devices_are_skipped(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"], "revoked-token", revoked=True)
    device(conn, chat["bob"], None)
    device(conn, chat["bob"], "good-token")
    assert pushed_tokens(conn, chat) == ["good-token"]


def test_user_who_blocked_the_sender_is_skipped(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"])
    conn.execute(
        "INSERT INTO user_blocks (blocker_id, blocked_id) VALUES (%s, %s)",
        (chat["bob"], chat["alice"]),
    )
    assert pushed_tokens(conn, chat) == []


def test_user_removed_from_the_tenant_is_skipped(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"])
    conn.execute(
        "UPDATE tenant_members SET removed_at = now() WHERE tenant_id = %s AND user_id = %s",
        (chat["tenant"], chat["bob"]),
    )
    assert pushed_tokens(conn, chat) == []


def test_dead_token_is_cleared(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"], "dead-token")
    result = deliver_push(conn, FakeSender(dead={"dead-token"}), chat["conv"], 1)
    assert result == {"sent": 0, "dead": 1, "failed": 0}
    token = conn.execute(
        "SELECT push_token FROM devices WHERE user_id = %s", (chat["bob"],)
    ).fetchone()[0]
    assert token is None


def test_a_failing_sender_does_not_stop_the_others(conn):
    chat = seed_chat(conn)
    message(conn, chat, 1)
    device(conn, chat["bob"], "bad")
    device(conn, chat["bob"], "good")

    class Flaky(FakeSender):
        def send(self, platform, token, payload):
            if token == "bad":
                raise TimeoutError("provider down")
            return super().send(platform, token, payload)

    result = deliver_push(conn, Flaky(), chat["conv"], 1)
    assert result == {"sent": 1, "dead": 0, "failed": 1}