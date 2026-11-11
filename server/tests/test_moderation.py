import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.core import db
from app.main import app
from app.moderation.blocks import blocked_between
from tests.helpers import seed_chat


@pytest.fixture
def client(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)
    db.close_pool()
    with TestClient(app) as c:
        yield c
    db.close_pool()


def hdr(chat, who="alice", tenant=None):
    return {
        "X-Dev-User-Id": str(chat[who]),
        "X-Dev-Tenant-Id": str(tenant or chat["tenant"]),
    }


def add_message(conn, chat, sender="bob"):
    conn.execute("UPDATE conversations SET last_seq = 1 WHERE id = %s", (chat["conv"],))
    conn.execute(
        "INSERT INTO messages (conversation_id, seq, sender_id, client_msg_id, kind, body) "
        "VALUES (%s, 1, %s, %s, 'text', 'hello')",
        (chat["conv"], chat[sender], uuid4()),
    )
    conn.commit()


def report_payload(chat, **overrides):
    payload = {"conversation_id": str(chat["conv"]), "seq": 1, "reason": "abusive language xyz"}
    payload.update(overrides)
    return payload


def test_block_is_idempotent_and_applies_both_ways(client, conn):
    chat = seed_chat(conn)
    for _ in range(2):
        r = client.post("/v1/blocks", json={"user_id": str(chat["bob"])}, headers=hdr(chat))
        assert r.status_code == 204
    assert conn.execute("SELECT count(*) FROM user_blocks").fetchone()[0] == 1
    assert blocked_between(conn, chat["alice"], chat["bob"]) is True
    assert blocked_between(conn, chat["bob"], chat["alice"]) is True
    assert blocked_between(conn, chat["alice"], chat["carol"]) is False


def test_cannot_block_self(client, conn):
    chat = seed_chat(conn)
    r = client.post("/v1/blocks", json={"user_id": str(chat["alice"])}, headers=hdr(chat))
    assert r.status_code == 422


def test_cannot_block_user_outside_tenant(client, conn):
    chat = seed_chat(conn)
    other = seed_chat(conn)
    r = client.post("/v1/blocks", json={"user_id": str(other["alice"])}, headers=hdr(chat))
    assert r.status_code == 404
    r = client.post("/v1/blocks", json={"user_id": str(uuid4())}, headers=hdr(chat))
    assert r.status_code == 404


def test_unblock_and_list(client, conn):
    chat = seed_chat(conn)
    client.post("/v1/blocks", json={"user_id": str(chat["bob"])}, headers=hdr(chat))
    listed = client.get("/v1/blocks", headers=hdr(chat)).json()
    assert [b["id"] for b in listed] == [str(chat["bob"])]
    assert listed[0]["display_name"] == "Bob"
    url = f"/v1/blocks/{chat['bob']}"
    assert client.delete(url, headers=hdr(chat)).status_code == 204
    assert client.get("/v1/blocks", headers=hdr(chat)).json() == []
    assert client.delete(url, headers=hdr(chat)).status_code == 204


def test_report_creates_row_and_audit_without_reason_text(client, conn):
    chat = seed_chat(conn)
    add_message(conn, chat)
    r = client.post("/v1/reports", json=report_payload(chat), headers=hdr(chat))
    assert r.status_code == 201
    assert r.json()["status"] == "open"
    report_id = r.json()["id"]
    again = client.post("/v1/reports", json=report_payload(chat), headers=hdr(chat))
    assert again.json()["id"] == report_id
    assert conn.execute("SELECT count(*) FROM reports").fetchone()[0] == 1
    reporter = conn.execute("SELECT reporter_id FROM reports").fetchone()[0]
    assert reporter == chat["alice"]
    action, target = conn.execute(
        "SELECT action, target FROM audit_log WHERE tenant_id = %s", (chat["tenant"],)
    ).fetchone()
    assert action == "report.create"
    assert "reason" not in target
    assert "xyz" not in json.dumps(target)


def test_cannot_report_own_message(client, conn):
    chat = seed_chat(conn)
    add_message(conn, chat, sender="alice")
    r = client.post("/v1/reports", json=report_payload(chat), headers=hdr(chat))
    assert r.status_code == 422


def test_non_member_cannot_report(client, conn):
    chat = seed_chat(conn)
    add_message(conn, chat)
    r = client.post("/v1/reports", json=report_payload(chat), headers=hdr(chat, "carol"))
    assert r.status_code == 404


def test_report_of_unknown_message_is_404(client, conn):
    chat = seed_chat(conn)
    add_message(conn, chat)
    r = client.post("/v1/reports", json=report_payload(chat, seq=99), headers=hdr(chat))
    assert r.status_code == 404


@pytest.mark.parametrize("reason", ["", "   ", "x" * 2001])
def test_report_reason_is_validated(client, conn, reason):
    chat = seed_chat(conn)
    r = client.post("/v1/reports", json=report_payload(chat, reason=reason), headers=hdr(chat))
    assert r.status_code == 422


def test_requires_auth(client):
    assert client.post("/v1/blocks", json={"user_id": str(uuid4())}).status_code == 401
    assert client.get("/v1/blocks").status_code == 401
    assert client.post("/v1/reports", json=report_payload({"conv": uuid4()})).status_code == 401