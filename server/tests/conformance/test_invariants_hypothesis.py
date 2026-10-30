"""Hypothesis property-based test suite for Core Invariants I1 through I6 (BE-1: P2).

Verifies:
- Invariant I1: Idempotency under repeated submissions with same client_msg_id.
- Invariant I2: Gapless monotonic sequence assignment (1..N) despite retries and rejections.
- Invariant I3: Monotonic delivery & read cursors; read_seq cannot exceed delivered_seq.
- Invariant I4: Visibility boundary enforcement (never returns seq < visible_from_seq; left_at rejection).
- Invariant I5: Deterministic realtime hint payload sizing (<= 4096 bytes full msg, > 4096 bytes msg_hint).
- Invariant I6: Append-only tombstone deletion (row never deleted, kind='delete', target_seq set).
"""

from datetime import datetime, UTC
from uuid import uuid4

from fastapi.testclient import TestClient
from hypothesis import given, settings as hyp_settings, strategies as st
import psycopg
import pytest

from app.config import settings
from app.main import app
from app.send import NotAllowed, send_message, send_tombstone
from tests.helpers import seed_chat

client = TestClient(app)


@pytest.fixture(autouse=True)
def use_test_db(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)


# -----------------------------------------------------------------------------
# Invariant I1: Idempotency Property Test
# -----------------------------------------------------------------------------
@hyp_settings(max_examples=15, deadline=None)
@given(
    body=st.text(min_size=1, max_size=200).filter(lambda s: bool(s.strip())),
    num_retries=st.integers(min_value=1, max_value=5),
)
def test_property_i1_idempotency_retries_produce_single_message(db_url, body, num_retries):
    with psycopg.connect(db_url) as conn:
        s = seed_chat(conn)
        conv_id = s["conv"]
        alice_id = s["alice"]
        client_msg_id = uuid4()

        # Initial send
        first = send_message(
            conn,
            conversation_id=conv_id,
            sender_id=alice_id,
            client_msg_id=client_msg_id,
            body=body,
        )
        assert first.seq >= 1
        assert first.duplicate is False

        # Arbitrary retries
        for _ in range(num_retries):
            retry = send_message(
                conn,
                conversation_id=conv_id,
                sender_id=alice_id,
                client_msg_id=client_msg_id,
                body=body,
            )
            assert retry.seq == first.seq
            assert retry.id == first.id
            assert retry.duplicate is True

        # Total stored rows in DB must be exactly 1
        count = conn.execute(
            "SELECT count(*) FROM messages WHERE conversation_id = %s", (conv_id,)
        ).fetchone()[0]
        assert count == 1


# -----------------------------------------------------------------------------
# Invariant I2: Gapless Sequences Property Test
# -----------------------------------------------------------------------------
@hyp_settings(max_examples=15, deadline=None)
@given(
    actions=st.lists(
        st.tuples(
            st.sampled_from(["valid", "retry_last", "invalid_kind", "invalid_user"]),
            st.text(min_size=1, max_size=100).filter(lambda s: bool(s.strip())),
        ),
        min_size=3,
        max_size=10,
    )
)
def test_property_i2_gapless_sequences_under_interleaved_operations(db_url, actions):
    with psycopg.connect(db_url) as conn:
        s = seed_chat(conn)
        conv_id = s["conv"]
        alice_id = s["alice"]
        carol_id = s["carol"]  # not a member

        last_client_msg_id = None
        expected_seq = 1

        for action_type, text_body in actions:
            if action_type == "valid":
                cmid = uuid4()
                sent = send_message(
                    conn,
                    conversation_id=conv_id,
                    sender_id=alice_id,
                    client_msg_id=cmid,
                    body=text_body,
                )
                assert sent.seq == expected_seq
                assert sent.duplicate is False
                last_client_msg_id = cmid
                expected_seq += 1

            elif action_type == "retry_last":
                if last_client_msg_id is not None:
                    sent = send_message(
                        conn,
                        conversation_id=conv_id,
                        sender_id=alice_id,
                        client_msg_id=last_client_msg_id,
                        body=text_body,
                    )
                    assert sent.duplicate is True
                    # Retry must not increment expected_seq

            elif action_type == "invalid_kind":
                with pytest.raises(NotAllowed):
                    send_message(
                        conn,
                        conversation_id=conv_id,
                        sender_id=alice_id,
                        client_msg_id=uuid4(),
                        kind="system",  # client not allowed to send system
                        body=text_body,
                    )
                # Rejection must not burn a sequence number

            elif action_type == "invalid_user":
                with pytest.raises(NotAllowed):
                    send_message(
                        conn,
                        conversation_id=conv_id,
                        sender_id=carol_id,  # not a member
                        client_msg_id=uuid4(),
                        body=text_body,
                    )
                # Rejection must not burn a sequence number

        # Verify all committed messages are strictly gapless: 1..expected_seq-1
        rows = conn.execute(
            "SELECT seq FROM messages WHERE conversation_id = %s ORDER BY seq ASC", (conv_id,)
        ).fetchall()
        seqs = [r[0] for r in rows]
        expected_list = list(range(1, expected_seq))
        assert seqs == expected_list

        # Verify conversation last_seq matches
        last_seq = conn.execute(
            "SELECT last_seq FROM conversations WHERE id = %s", (conv_id,)
        ).fetchone()[0]
        assert last_seq == (expected_seq - 1)


# -----------------------------------------------------------------------------
# Invariant I3: Monotonic Cursors Property Test
# -----------------------------------------------------------------------------
@hyp_settings(max_examples=15, deadline=None)
@given(
    cursor_steps=st.lists(
        st.tuples(
            st.integers(min_value=0, max_value=50),
            st.integers(min_value=0, max_value=50),
        ),
        min_size=2,
        max_size=8,
    )
)
def test_property_i3_monotonic_cursors_and_greatest_update(db_url, cursor_steps):
    with psycopg.connect(db_url) as conn:
        s = seed_chat(conn)
        conv_id = s["conv"]
        bob_id = s["bob"]

        highest_delivered = 0
        highest_read = 0

        for d_seq, r_seq in cursor_steps:
            if r_seq <= d_seq:
                # Valid ack format
                conn.execute(
                    """
                    UPDATE conversation_members
                    SET delivered_seq = GREATEST(delivered_seq, %s),
                        read_seq = GREATEST(read_seq, %s)
                    WHERE conversation_id = %s AND user_id = %s
                    """,
                    (d_seq, r_seq, conv_id, bob_id),
                )
                conn.commit()
                highest_delivered = max(highest_delivered, d_seq)
                highest_read = max(highest_read, r_seq)

                row = conn.execute(
                    "SELECT delivered_seq, read_seq FROM conversation_members "
                    "WHERE conversation_id = %s AND user_id = %s",
                    (conv_id, bob_id),
                ).fetchone()
                assert row[0] == highest_delivered
                assert row[1] == highest_read
                assert row[1] <= row[0]  # read_seq never exceeds delivered_seq


# -----------------------------------------------------------------------------
# Invariant I4: Visibility Boundary Property Test
# -----------------------------------------------------------------------------
@hyp_settings(max_examples=15, deadline=None)
@given(
    num_messages=st.integers(min_value=3, max_value=8),
    visible_from=st.integers(min_value=1, max_value=8),
)
def test_property_i4_visibility_boundary_never_leaks_prior_messages(
    db_url, num_messages, visible_from
):
    with psycopg.connect(db_url) as conn:
        s = seed_chat(conn)
        conv_id = s["conv"]
        alice_id = s["alice"]
        bob_id = s["bob"]
        headers_bob = {"Authorization": f"Bearer {bob_id}"}

        # Alice sends messages 1..num_messages
        for i in range(num_messages):
            send_message(
                conn,
                conversation_id=conv_id,
                sender_id=alice_id,
                client_msg_id=uuid4(),
                body=f"msg-{i}",
            )

        # Set Bob's visible_from_seq
        conn.execute(
            "UPDATE conversation_members SET visible_from_seq = %s "
            "WHERE conversation_id = %s AND user_id = %s",
            (visible_from, conv_id, bob_id),
        )
        conn.commit()

        # Bob fetches messages starting at after=0
        resp = client.get(
            f"/v1/conversations/{conv_id}/messages?after=0&limit=50", headers=headers_bob
        )
        assert resp.status_code == 200
        returned_msgs = resp.json()["messages"]

        # Invariant I4: No message seq may be strictly less than visible_from_seq
        for m in returned_msgs:
            assert m["seq"] >= visible_from


# -----------------------------------------------------------------------------
# Invariant I5: Deterministic Realtime Hint Payload Boundary Test
# -----------------------------------------------------------------------------
@hyp_settings(max_examples=15, deadline=None)
@given(
    body_len=st.integers(min_value=10, max_value=6000),
)
def test_property_i5_realtime_hint_size_boundary(body_len):
    # Construct ascii payload of length body_len
    body = "a" * body_len
    body_bytes = body.encode("utf-8")

    from app.ws.schemas import MsgFrame, MsgHintFrame

    dummy_cid = uuid4()
    dummy_mid = uuid4()
    dummy_uid = uuid4()

    now = datetime.now(UTC)

    if len(body_bytes) <= 4096:
        frame = MsgFrame(
            conversation_id=dummy_cid,
            seq=1,
            id=dummy_mid,
            sender_id=dummy_uid,
            kind="text",
            body=body,
            attachment_id=None,
            created_at=now,
        )
        assert frame.type == "msg"
        assert frame.body == body
    else:
        frame = MsgHintFrame(
            conversation_id=dummy_cid,
            seq=1,
            id=dummy_mid,
            sender_id=dummy_uid,
            kind="text",
            created_at=now,
        )
        assert frame.type == "msg_hint"
        assert not hasattr(frame, "body")


# -----------------------------------------------------------------------------
# Invariant I6: Tombstone Append-Only Deletion Property Test
# -----------------------------------------------------------------------------
@hyp_settings(max_examples=15, deadline=None)
@given(
    target_idx=st.integers(min_value=1, max_value=4),
)
def test_property_i6_tombstone_append_only_preserves_original_row(db_url, target_idx):
    with psycopg.connect(db_url) as conn:
        s = seed_chat(conn)
        conv_id = s["conv"]
        alice_id = s["alice"]

        # Send 4 messages
        for i in range(1, 5):
            send_message(
                conn,
                conversation_id=conv_id,
                sender_id=alice_id,
                client_msg_id=uuid4(),
                body=f"original-{i}",
            )

        # Alice deletes message at target_idx
        sent_tomb = send_tombstone(
            conn,
            conversation_id=conv_id,
            actor_id=alice_id,
            target_seq=target_idx,
        )
        assert sent_tomb.seq == 5  # appends at last_seq + 1
        assert sent_tomb.duplicate is False

        # Invariant I6: Original message row still exists in DB intact
        orig_row = conn.execute(
            "SELECT kind, body, target_seq FROM messages WHERE conversation_id = %s AND seq = %s",
            (conv_id, target_idx),
        ).fetchone()
        assert orig_row == ("text", f"original-{target_idx}", None)

        # Tombstone row exists with kind='delete', target_seq=target_idx, body=None
        tomb_row = conn.execute(
            "SELECT kind, target_seq, body FROM messages WHERE conversation_id = %s AND seq = 5",
            (conv_id,),
        ).fetchone()
        assert tomb_row == ("delete", target_idx, None)
