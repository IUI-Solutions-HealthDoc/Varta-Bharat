from uuid import uuid4

from app.core.audit import audit


def test_audit_writes_row(conn):
    tenant, actor = uuid4(), uuid4()
    audit_id = audit(
        conn, tenant, actor, "member.remove", {"user_id": "u1", "conversation": "c1"}, ip="203.0.113.7"
    )
    row = conn.execute(
        "SELECT tenant_id, actor_id, action, target, host(ip) FROM audit_log WHERE id = %s",
        (audit_id,),
    ).fetchone()
    assert row == (tenant, actor, "member.remove", {"user_id": "u1", "conversation": "c1"}, "203.0.113.7")


def test_audit_allows_system_actor_and_no_ip(conn):
    audit_id = audit(conn, uuid4(), None, "retention.run", {"deleted": 3})
    row = conn.execute("SELECT actor_id, ip FROM audit_log WHERE id = %s", (audit_id,)).fetchone()
    assert row == (None, None)


def test_audit_rolls_back_with_caller(conn):
    audit(conn, uuid4(), None, "x", {})
    conn.rollback()
    assert conn.execute("SELECT count(*) FROM audit_log").fetchone()[0] == 0
