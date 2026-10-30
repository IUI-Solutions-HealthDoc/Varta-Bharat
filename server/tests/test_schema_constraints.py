import uuid

import psycopg
import pytest

from tests.helpers import seed_chat


def test_uuidv7_available(conn):
    u = conn.execute("SELECT uuidv7()").fetchone()[0]
    assert str(u)[14] == "7"


def test_dm_requires_dm_key(conn):
    s = seed_chat(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO conversations (tenant_id, kind, created_by) VALUES (%s, 'dm', %s)",
            (s["tenant"], s["alice"]),
        )
    conn.rollback()


def test_non_dm_cannot_have_dm_key(conn):
    s = seed_chat(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO conversations (tenant_id, kind, dm_key, created_by) "
            "VALUES (%s, 'private', 'x', %s)",
            (s["tenant"], s["alice"]),
        )
    conn.rollback()


def test_one_dm_per_pair(conn):
    s = seed_chat(conn)
    q = "INSERT INTO conversations (tenant_id, kind, dm_key, created_by) VALUES (%s, 'dm', %s, %s)"
    key = f"{s['tenant']}:{s['alice']}:{s['bob']}"
    conn.execute(q, (s["tenant"], key, s["alice"]))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(q, (s["tenant"], key, s["alice"]))
    conn.rollback()


def test_read_cannot_exceed_delivered(conn):
    s = seed_chat(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "UPDATE conversation_members SET read_seq = 5, delivered_seq = 2 "
            "WHERE conversation_id = %s AND user_id = %s",
            (s["conv"], s["bob"]),
        )
    conn.rollback()


def test_duplicate_client_msg_id_rejected_by_constraint(conn):
    s = seed_chat(conn)
    cmid = uuid.uuid4()
    q = (
        "INSERT INTO messages (conversation_id, seq, sender_id, client_msg_id, kind, body) "
        "VALUES (%s, %s, %s, %s, 'text', 'hi')"
    )
    conn.execute(q, (s["conv"], 1, s["alice"], cmid))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(q, (s["conv"], 2, s["alice"], cmid))
    conn.rollback()


def test_invite_cannot_grant_admin(conn):
    s = seed_chat(conn)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO invitations (tenant_id, token_hash, grants_role, expires_at, created_by) "
            "VALUES (%s, %s, 'admin', now() + interval '1 day', %s)",
            (s["tenant"], b"h" * 32, s["alice"]),
        )
    conn.rollback()


def test_invite_redemption_respects_max_uses(conn):
    s = seed_chat(conn)
    conn.execute(
        "INSERT INTO invitations (tenant_id, token_hash, max_uses, expires_at, created_by) "
        "VALUES (%s, %s, 1, now() + interval '1 day', %s)",
        (s["tenant"], b"t" * 32, s["alice"]),
    )
    redeem = (
        "UPDATE invitations SET used_count = used_count + 1 "
        "WHERE token_hash = %s AND revoked_at IS NULL AND expires_at > now() "
        "AND (max_uses IS NULL OR used_count < max_uses) RETURNING id"
    )
    assert conn.execute(redeem, (b"t" * 32,)).fetchone() is not None
    assert conn.execute(redeem, (b"t" * 32,)).fetchone() is None
    conn.rollback()


def test_app_role_cannot_modify_audit_log(conn):
    s = seed_chat(conn)
    conn.execute(
        "INSERT INTO audit_log (tenant_id, action, target) VALUES (%s, 'test', '{}')",
        (s["tenant"],),
    )
    conn.commit()
    conn.execute("SET ROLE varta_app")
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 1
    conn.execute(
        "INSERT INTO audit_log (tenant_id, action, target) VALUES (%s, 't2', '{}')", (s["tenant"],)
    )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("UPDATE audit_log SET action = 'tampered'")
    conn.rollback()
    conn.execute("RESET ROLE")
