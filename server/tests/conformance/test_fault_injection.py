"""Fault-injection and resilience test suite (BE-1: P2 Polish & Robustness).

Tests system behavior under simulated infrastructure and transaction faults:
1. Mid-transaction crash after last_seq bump -> Rolls back transaction, burning zero sequence numbers (Invariant I2).
2. Post-commit Valkey outage -> Committed DB message is NOT aborted or lost; client receives success.
3. Post-commit Push notification failure -> Message is safely stored and delivered; push failure logged.
4. Blocked user attempt mid-send -> Rejected cleanly, leaves no gaps.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import psycopg
import pytest

from app.config import settings
from app.send import NotAllowed, enqueue_push, send_message
from tests.helpers import seed_chat


@pytest.fixture(autouse=True)
def use_test_db(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)


def test_fault_mid_transaction_rollback_preserves_gapless_sequence(db_url):
    """Simulates a database failure or unhandled exception inside the transaction

    after last_seq = last_seq + 1 has been executed. The rollback must undo
    the sequence increment, preserving Invariant I2.
    """
    with psycopg.connect(db_url, autocommit=True) as conn:
        s = seed_chat(conn)
        conv_id = s["conv"]
        alice_id = s["alice"]

        # 1. Normal message 1 succeeds
        m1 = send_message(
            conn,
            conversation_id=conv_id,
            sender_id=alice_id,
            client_msg_id=uuid4(),
            body="Message 1",
        )
        assert m1.seq == 1

        # 2. Injected fault: simulate an error right after bumping last_seq
        with pytest.raises(RuntimeError, match="Simulated crash mid-transaction"):
            with conn.transaction():
                conn.execute(
                    "UPDATE conversations SET last_seq = last_seq + 1 WHERE id = %s",
                    (conv_id,),
                )
                # Simulated crash before message insertion
                raise RuntimeError("Simulated crash mid-transaction")

        # 3. Check conversations.last_seq: must still be 1 (rollback undid the bump!)
        last_seq = conn.execute(
            "SELECT last_seq FROM conversations WHERE id = %s", (conv_id,)
        ).fetchone()[0]
        assert last_seq == 1

        # 4. Next normal send gets gapless seq 2 (Invariant I2: zero burned sequences)
        m2 = send_message(
            conn,
            conversation_id=conv_id,
            sender_id=alice_id,
            client_msg_id=uuid4(),
            body="Message 2 after fault",
        )
        assert m2.seq == 2

        # Verify rows in DB are strictly [1, 2]
        rows = conn.execute(
            "SELECT seq FROM messages WHERE conversation_id = %s ORDER BY seq ASC", (conv_id,)
        ).fetchall()
        assert [r[0] for r in rows] == [1, 2]


def test_fault_post_commit_valkey_outage_does_not_abort_message(db_url):
    """If Valkey is unavailable or raises ConnectionError during post-commit hint publishing,

    the already-committed database message must still succeed and return to the client.
    """
    with psycopg.connect(db_url, autocommit=True) as conn:
        s = seed_chat(conn)
        conv_id = s["conv"]
        alice_id = s["alice"]

        with patch("app.core.valkey.get_valkey") as mock_valkey:
            mock_valkey.side_effect = ConnectionError(
                "Valkey cluster unreachable (simulated fault)"
            )

            # Send should succeed despite Valkey outage
            sent = send_message(
                conn,
                conversation_id=conv_id,
                sender_id=alice_id,
                client_msg_id=uuid4(),
                body="Message during Valkey outage",
            )
            assert sent.seq == 1
            assert sent.duplicate is False

        # Message must exist in the database
        db_row = conn.execute(
            "SELECT seq, body FROM messages WHERE conversation_id = %s AND seq = 1", (conv_id,)
        ).fetchone()
        assert db_row == (1, "Message during Valkey outage")


def test_fault_post_commit_push_hook_failure_does_not_fail_send(db_url):
    """If push notification enqueuing fails (e.g. worker error),

    enqueue_push handles the failure gracefully without crashing the send.
    """
    with psycopg.connect(db_url, autocommit=True) as conn:
        s = seed_chat(conn)
        conv_id = s["conv"]
        alice_id = s["alice"]

        mock_push_module = MagicMock()
        mock_push_module.enqueue_push.side_effect = Exception("Push notification queue timeout")

        with patch.dict("sys.modules", {"app.push": mock_push_module}):
            # enqueue_push must not raise
            enqueue_push(conv_id, 1)

            # send_message must also complete cleanly
            sent = send_message(
                conn,
                conversation_id=conv_id,
                sender_id=alice_id,
                client_msg_id=uuid4(),
                body="Message with push failure",
            )
            assert sent.seq == 1

        db_row = conn.execute(
            "SELECT seq FROM messages WHERE conversation_id = %s AND seq = 1", (conv_id,)
        ).fetchone()
        assert db_row == (1,)


def test_fault_blocked_user_in_dm_leaves_no_gap(db_url):
    """If a user attempts to send a message to a DM while blocked,

    the request is rejected with NotAllowed and leaves no sequence gap.
    """
    with psycopg.connect(db_url, autocommit=True) as conn:
        s = seed_chat(conn)
        tenant = s["tenant"]
        alice = s["alice"]
        bob = s["bob"]

        # Create DM conversation with valid dm_key constraint
        dm_key = f"dm:{min(alice, bob)}:{max(alice, bob)}"
        dm_conv = conn.execute(
            "INSERT INTO conversations (tenant_id, kind, dm_key, created_by) "
            "VALUES (%s, 'dm', %s, %s) RETURNING id",
            (tenant, dm_key, alice),
        ).fetchone()[0]

        for uid in (alice, bob):
            conn.execute(
                "INSERT INTO conversation_members (conversation_id, user_id, role) "
                "VALUES (%s, %s, 'member')",
                (dm_conv, uid),
            )

        # Bob blocks Alice
        conn.execute(
            "INSERT INTO user_blocks (blocker_id, blocked_id) VALUES (%s, %s)",
            (bob, alice),
        )

        # Alice attempts to send -> rejected with NotAllowed
        with pytest.raises(NotAllowed, match="user is blocked"):
            send_message(
                conn,
                conversation_id=dm_conv,
                sender_id=alice,
                client_msg_id=uuid4(),
                body="Should fail due to block",
            )

        # Sequence must still be 0, no messages stored
        last_seq = conn.execute(
            "SELECT last_seq FROM conversations WHERE id = %s", (dm_conv,)
        ).fetchone()[0]
        assert last_seq == 0

        count = conn.execute(
            "SELECT count(*) FROM messages WHERE conversation_id = %s", (dm_conv,)
        ).fetchone()[0]
        assert count == 0
