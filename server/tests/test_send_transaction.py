import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest

from app.send import NotAllowed, send_message
from tests.helpers import seed_chat


def _count(conn, conv):
    return conn.execute("SELECT count(*) FROM messages WHERE conversation_id = %s", (conv,)).fetchone()[0]


def _last_seq(conn, conv):
    return conn.execute("SELECT last_seq FROM conversations WHERE id = %s", (conv,)).fetchone()[0]


def test_seq_is_gapless_and_increasing(conn):
    s = seed_chat(conn)
    seqs = [
        send_message(conn, conversation_id=s["conv"], sender_id=s["alice"],
                     client_msg_id=uuid.uuid4(), body=f"m{i}").seq
        for i in range(3)
    ]
    assert seqs == [1, 2, 3]


def test_retry_returns_original_and_leaves_no_gap(conn):
    s = seed_chat(conn)
    cmid = uuid.uuid4()
    first = send_message(conn, conversation_id=s["conv"], sender_id=s["alice"], client_msg_id=cmid, body="hi")
    again = send_message(conn, conversation_id=s["conv"], sender_id=s["alice"], client_msg_id=cmid, body="hi")
    nxt = send_message(conn, conversation_id=s["conv"], sender_id=s["alice"], client_msg_id=uuid.uuid4(), body="2")
    assert (first.seq, first.duplicate) == (1, False)
    assert (again.seq, again.id, again.duplicate) == (1, first.id, True)
    assert nxt.seq == 2  # no gap after the retry
    assert _count(conn, s["conv"]) == 2
    assert _last_seq(conn, s["conv"]) == 2


def test_100_concurrent_sends_are_gapless(conn, db_url):
    s = seed_chat(conn)

    def work(i):
        with psycopg.connect(db_url) as c:
            return send_message(
                c, conversation_id=s["conv"], sender_id=s["alice" if i % 2 else "bob"],
                client_msg_id=uuid.uuid4(), body=f"m{i}",
            ).seq

    with ThreadPoolExecutor(max_workers=10) as ex:
        seqs = list(ex.map(work, range(100)))
    assert sorted(seqs) == list(range(1, 101))
    assert _count(conn, s["conv"]) == 100
    assert _last_seq(conn, s["conv"]) == 100


def test_concurrent_retries_produce_one_message(conn, db_url):
    s = seed_chat(conn)
    cmid = uuid.uuid4()

    def work(_):
        with psycopg.connect(db_url) as c:
            return send_message(c, conversation_id=s["conv"], sender_id=s["alice"],
                                client_msg_id=cmid, body="same").seq

    with ThreadPoolExecutor(max_workers=10) as ex:
        seqs = list(ex.map(work, range(20)))
    assert set(seqs) == {1}
    assert _count(conn, s["conv"]) == 1
    assert _last_seq(conn, s["conv"]) == 1


def test_non_member_rejected_without_burning_a_seq(conn):
    s = seed_chat(conn)
    with pytest.raises(NotAllowed):
        send_message(conn, conversation_id=s["conv"], sender_id=s["carol"],
                     client_msg_id=uuid.uuid4(), body="hi")
    assert _last_seq(conn, s["conv"]) == 0


def test_member_who_left_is_rejected(conn):
    s = seed_chat(conn)
    conn.execute(
        "UPDATE conversation_members SET left_at = now() WHERE conversation_id = %s AND user_id = %s",
        (s["conv"], s["bob"]),
    )
    conn.commit()
    with pytest.raises(NotAllowed):
        send_message(conn, conversation_id=s["conv"], sender_id=s["bob"],
                     client_msg_id=uuid.uuid4(), body="hi")
    assert _last_seq(conn, s["conv"]) == 0


def test_only_admins_post_in_announcement_channels(conn):
    s = seed_chat(conn, conv_kind="announcement")
    with pytest.raises(NotAllowed):
        send_message(conn, conversation_id=s["conv"], sender_id=s["bob"],
                     client_msg_id=uuid.uuid4(), body="hi")
    ok = send_message(conn, conversation_id=s["conv"], sender_id=s["alice"],
                      client_msg_id=uuid.uuid4(), body="notice")
    assert ok.seq == 1


def test_body_is_normalised_to_nfc(conn):
    s = seed_chat(conn)
    send_message(conn, conversation_id=s["conv"], sender_id=s["alice"],
                 client_msg_id=uuid.uuid4(), body="e\u0301")  # e + combining acute
    body = conn.execute("SELECT body FROM messages WHERE conversation_id = %s", (s["conv"],)).fetchone()[0]
    assert body == "\u00e9"
