"""Security conformance test suite verifying real JWT authentication, device revocation, and IDOR prevention.

Covers:
1. redeem_ws_ticket:
   - Arbitrary string of 16+ characters is rejected.
   - Legacy test:<user_id>:<tenant_id> dev ticket is rejected in all environments.
   - Tickets created by POST /v1/ws-ticket in Valkey are accepted.
   - Single-use invariant (Plan D-5): Second redemption attempt is rejected.
2. WebSocket membership enforcement (Plan I4 & section 9.1 IDOR prevention):
   - subscribe frame from non-member is rejected with FORBIDDEN and socket not added.
   - subscribe frame from member with left_at IS NOT NULL is rejected.
   - subscribe frame from removed tenant member is rejected.
   - subscribe frame from inactive (suspended) user is rejected.
   - ack frame from non-member is rejected with FORBIDDEN and socket not added.
   - typing frame from non-member is rejected with FORBIDDEN, not broadcast, socket not added.
   - Cross-conversation eavesdropping (IDOR) is completely prevented.
3. Real JWT authentication & device session checks:
   - Old dev headers (no header, X-User-Id, Bearer <uuid>) are rejected with 401.
   - Token for a revoked device is rejected with 401 on send and on POST /v1/ws-ticket.
   - Cross-tenant and unauthorized device revocations are rejected (404 / 403).
"""

from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.main import app
from app.ws.router import redeem_ws_ticket
from tests.helpers import auth_headers, seed_chat

client = TestClient(app)


@pytest.fixture(autouse=True)
def use_test_db(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)


def _get_ws_ticket(chat: dict, who: str = "bob", headers: dict | None = None) -> str:
    hdrs = headers if headers is not None else auth_headers(chat, who)
    r = client.post("/v1/ws-ticket", headers=hdrs)
    assert r.status_code == 200
    return r.json()["ticket"]


# =============================================================================
# 1. WebSocket Ticket Security Tests
# =============================================================================


def test_redeem_ws_ticket_rejects_arbitrary_16_char_ticket():
    """Any arbitrary ticket >= 16 characters or wstk_ format without Valkey entry is rejected."""
    assert redeem_ws_ticket("a" * 16) is None
    assert redeem_ws_ticket("wstk_randomstring1234567890") is None
    assert redeem_ws_ticket("random_ticket_not_in_valkey") is None

    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"type": "hello", "ticket": "arbitrary_long_ticket_123456"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "INVALID_TICKET"


def test_redeem_ws_ticket_rejects_dev_ticket_in_all_environments(monkeypatch):
    """Legacy dev tickets (test:<user>:<tenant>) are rejected in all environments including local."""
    uid = uuid4()
    tid = uuid4()
    dev_ticket = f"test:{uid}:{tid}"

    for env in ("local", "production", "staging", "testing"):
        monkeypatch.setattr(settings, "environment", env)
        assert redeem_ws_ticket(dev_ticket) is None

        with client.websocket_connect("/v1/ws") as ws:
            ws.send_json({"type": "hello", "ticket": dev_ticket})
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "INVALID_TICKET"


def test_ws_ticket_valkey_lifecycle_and_single_use(conn):
    """Tickets issued via POST /v1/ws-ticket pass, and cannot be reused (single-use Plan D-5)."""
    s = seed_chat(conn)
    bob_id = s["bob"]
    headers = auth_headers(s, "bob")

    # 1. Request ticket via POST /v1/ws-ticket
    resp = client.post("/v1/ws-ticket", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "ticket" in data
    assert data["ticket"].startswith("wstk_")
    assert data["expires_in"] == 30
    ticket = data["ticket"]

    # 2. First WebSocket connection with ticket succeeds
    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"type": "hello", "ticket": ticket})
        welcome = ws.receive_json()
        assert welcome["type"] == "welcome"
        assert welcome["user_id"] == str(bob_id)

    # 3. Second redemption attempt with the same ticket is rejected (single-use!)
    with client.websocket_connect("/v1/ws") as ws2:
        ws2.send_json({"type": "hello", "ticket": ticket})
        err = ws2.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "INVALID_TICKET"


# =============================================================================
# 2. WebSocket Membership & IDOR Security Tests
# =============================================================================


def test_subscribe_frame_rejects_non_member_and_prevents_idor(conn):
    """A user cannot subscribe to a conversation they are not a member of (IDOR prevention)."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    ticket_carol = _get_ws_ticket(s, "carol")
    headers_alice = auth_headers(s, "alice")

    with client.websocket_connect("/v1/ws") as ws_carol:
        ws_carol.send_json({"type": "hello", "ticket": ticket_carol})
        assert ws_carol.receive_json()["type"] == "welcome"

        # Carol attempts to subscribe to Alice & Bob's conversation
        ws_carol.send_json(
            {
                "type": "subscribe",
                "conversation_id": str(conv_id),
            }
        )

        # Must be rejected with FORBIDDEN
        err = ws_carol.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "FORBIDDEN"
        assert "Not an active member" in err["message"]

        # Alice sends a message in conv_id
        msg_body = "Confidential conversation between Alice and Bob"
        r = client.post(
            f"/v1/conversations/{conv_id}/messages",
            json={"client_msg_id": str(uuid4()), "kind": "text", "body": msg_body},
            headers=headers_alice,
        )
        assert r.status_code == 201

        # Carol sends ping/pong to confirm socket is alive, but Carol NEVER gets the message
        ws_carol.send_json({"type": "ping"})
        pong = ws_carol.receive_json()
        assert pong == {"type": "pong"}


def test_subscribe_frame_rejects_user_who_left_conversation(conn):
    """A user who left the conversation (left_at IS NOT NULL) cannot subscribe (Invariant I4)."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    bob_id = s["bob"]
    ticket_bob = _get_ws_ticket(s, "bob")

    # Bob leaves the conversation
    conn.execute(
        "UPDATE conversation_members SET left_at = now() WHERE conversation_id = %s AND user_id = %s",
        (conv_id, bob_id),
    )
    conn.commit()

    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"type": "hello", "ticket": ticket_bob})
        assert ws.receive_json()["type"] == "welcome"

        # Bob attempts to subscribe to left conversation
        ws.send_json(
            {
                "type": "subscribe",
                "conversation_id": str(conv_id),
            }
        )
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "FORBIDDEN"


def test_subscribe_frame_rejects_removed_tenant_member(conn):
    """A user removed from the tenant (removed_at IS NOT NULL) cannot subscribe."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    bob_id = s["bob"]
    tenant_id = s["tenant"]
    ticket_bob = _get_ws_ticket(s, "bob")

    # Bob removed from tenant
    conn.execute(
        "UPDATE tenant_members SET removed_at = now() WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, bob_id),
    )
    conn.commit()

    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"type": "hello", "ticket": ticket_bob})
        assert ws.receive_json()["type"] == "welcome"

        ws.send_json(
            {
                "type": "subscribe",
                "conversation_id": str(conv_id),
            }
        )
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "FORBIDDEN"


def test_subscribe_frame_rejects_inactive_user(conn):
    """A user whose account is suspended or deleted cannot subscribe."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    bob_id = s["bob"]
    ticket_bob = _get_ws_ticket(s, "bob")

    # Bob suspended
    conn.execute(
        "UPDATE users SET status = 'suspended' WHERE id = %s",
        (bob_id,),
    )
    conn.commit()

    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"type": "hello", "ticket": ticket_bob})
        assert ws.receive_json()["type"] == "welcome"

        ws.send_json(
            {
                "type": "subscribe",
                "conversation_id": str(conv_id),
            }
        )
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "FORBIDDEN"


def test_ack_frame_rejects_non_member(conn):
    """An ack frame from a non-member is rejected with FORBIDDEN and does not subscribe."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    ticket_carol = _get_ws_ticket(s, "carol")

    with client.websocket_connect("/v1/ws") as ws_carol:
        ws_carol.send_json({"type": "hello", "ticket": ticket_carol})
        assert ws_carol.receive_json()["type"] == "welcome"

        # Carol sends ack for conv_id
        ws_carol.send_json(
            {
                "type": "ack",
                "conversation_id": str(conv_id),
                "delivered_seq": 1,
                "read_seq": 1,
            }
        )
        err = ws_carol.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "FORBIDDEN"
        assert "Not an active member" in err["message"]


def test_typing_frame_rejects_non_member(conn):
    """A typing frame from a non-member is rejected and not broadcast."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    ticket_bob = _get_ws_ticket(s, "bob")
    ticket_carol = _get_ws_ticket(s, "carol")

    with client.websocket_connect("/v1/ws") as ws_bob:
        ws_bob.send_json({"type": "hello", "ticket": ticket_bob})
        assert ws_bob.receive_json()["type"] == "welcome"

        with client.websocket_connect("/v1/ws") as ws_carol:
            ws_carol.send_json({"type": "hello", "ticket": ticket_carol})
            assert ws_carol.receive_json()["type"] == "welcome"

            # Carol attempts to send typing in conv_id
            ws_carol.send_json(
                {
                    "type": "typing",
                    "conversation_id": str(conv_id),
                    "is_typing": True,
                }
            )
            err = ws_carol.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "FORBIDDEN"

            # Bob must not receive any typing frame from Carol
            ws_bob.send_json({"type": "ping"})
            pong = ws_bob.receive_json()
            assert pong == {"type": "pong"}


# =============================================================================
# 3. Real Bearer Authentication & Revoked Device Security Tests
# =============================================================================


def test_legacy_stub_headers_and_unauthenticated_requests_get_401(conn):
    """Old dev headers (X-User-Id, Bearer <uuid>, no header) are rejected with 401."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    alice_id = s["alice"]
    tenant_id = s["tenant"]

    invalid_header_sets = [
        {},
        {"X-User-Id": str(alice_id)},
        {
            "X-User-Id": str(alice_id),
            "X-Tenant-Id": str(tenant_id),
            "X-Device-Id": str(uuid4()),
        },
        {"Authorization": f"Bearer {alice_id}"},
    ]

    for hdrs in invalid_header_sets:
        r_send = client.post(
            f"/v1/conversations/{conv_id}/messages",
            json={"client_msg_id": str(uuid4()), "kind": "text", "body": "unauthorized"},
            headers=hdrs,
        )
        assert r_send.status_code == 401

        r_sync = client.get("/v1/sync/conversations", headers=hdrs)
        assert r_sync.status_code == 401

        r_hist = client.get(f"/v1/conversations/{conv_id}/messages", headers=hdrs)
        assert r_hist.status_code == 401

        r_del = client.delete(f"/v1/conversations/{conv_id}/messages/1", headers=hdrs)
        assert r_del.status_code == 401

        r_ticket = client.post("/v1/ws-ticket", headers=hdrs)
        assert r_ticket.status_code == 401


def test_revoked_device_token_gets_401_on_send_and_ws_ticket(conn):
    """A JWT token belonging to a revoked device is rejected with 401 on send and /v1/ws-ticket."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    alice_id = s["alice"]
    headers_alice = auth_headers(s, "alice")

    # 1. While device is active, send and ws-ticket succeed
    r_ok = client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"client_msg_id": str(uuid4()), "kind": "text", "body": "before revoke"},
        headers=headers_alice,
    )
    assert r_ok.status_code == 201

    r_ticket_ok = client.post("/v1/ws-ticket", headers=headers_alice)
    assert r_ticket_ok.status_code == 200

    # 2. Revoke Alice's device in the database
    conn.execute(
        "UPDATE devices SET revoked_at = now() WHERE user_id = %s",
        (alice_id,),
    )
    conn.commit()

    # 3. Send with token for revoked device -> 401
    r_send_revoked = client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"client_msg_id": str(uuid4()), "kind": "text", "body": "after revoke"},
        headers=headers_alice,
    )
    assert r_send_revoked.status_code == 401

    # 4. Request /v1/ws-ticket with token for revoked device -> 401
    r_ticket_revoked = client.post("/v1/ws-ticket", headers=headers_alice)
    assert r_ticket_revoked.status_code == 401


def test_revoke_device_rejects_unauthenticated_and_other_user(conn):
    """POST /v1/devices/{device_id}/revoke requires authentication, device ownership, or admin role."""
    s = seed_chat(conn)
    alice_id = s["alice"]
    headers_alice = auth_headers(s, "alice")
    headers_bob = auth_headers(s, "bob")

    alice_device = uuid4()
    conn.execute(
        "INSERT INTO devices (id, user_id, platform, push_token, refresh_hash, refresh_family) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (alice_device, alice_id, "android", "push_token_alice", b"hash_alice", uuid4()),
    )
    conn.commit()

    # 1. Unauthenticated is rejected with 401
    r_unauth = client.post(f"/v1/devices/{alice_device}/revoke")
    assert r_unauth.status_code == 401

    # 2. Bob (non-owner, member role) attempts to revoke Alice's device -> 403 Forbidden
    r_bob = client.post(f"/v1/devices/{alice_device}/revoke", headers=headers_bob)
    assert r_bob.status_code == 403
    assert "Not authorized" in r_bob.json()["detail"]

    # 3. Alice (device owner) revokes her own device -> 200 OK
    r_alice = client.post(f"/v1/devices/{alice_device}/revoke", headers=headers_alice)
    assert r_alice.status_code == 200
    assert r_alice.json()["revoked"] is True


def test_live_socket_drops_unsubscribed_when_user_leaves_conversation(conn):
    """Connected WebSocket stops receiving live frames after user leaves conversation (Invariant I4)."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    bob_id = s["bob"]
    ticket_bob = _get_ws_ticket(s, "bob")
    headers_alice = auth_headers(s, "alice")

    with client.websocket_connect("/v1/ws") as ws_bob:
        ws_bob.send_json({"type": "hello", "ticket": ticket_bob})
        assert ws_bob.receive_json()["type"] == "welcome"

        # Alice sends message 1 while Bob is an active member
        r1 = client.post(
            f"/v1/conversations/{conv_id}/messages",
            json={"client_msg_id": str(uuid4()), "kind": "text", "body": "Live message 1"},
            headers=headers_alice,
        )
        assert r1.status_code == 201
        m1 = ws_bob.receive_json()
        assert m1["type"] == "msg"
        assert m1["body"] == "Live message 1"

        # Bob leaves the conversation
        conn.execute(
            "UPDATE conversation_members SET left_at = now() WHERE conversation_id = %s AND user_id = %s",
            (conv_id, bob_id),
        )
        conn.commit()

        # Alice sends message 2
        r2 = client.post(
            f"/v1/conversations/{conv_id}/messages",
            json={
                "client_msg_id": str(uuid4()),
                "kind": "text",
                "body": "Live message 2 after leave",
            },
            headers=headers_alice,
        )
        assert r2.status_code == 201

        # Bob should NOT receive message 2. Socket is still responsive (ping/pong works).
        ws_bob.send_json({"type": "ping"})
        pong = ws_bob.receive_json()
        assert pong == {"type": "pong"}


def test_sync_and_get_messages_rejects_removed_tenant_member_and_inactive_user(conn):
    """GET /messages and GET /sync/conversations reject removed tenant members and inactive users."""
    s = seed_chat(conn)
    conv_id = s["conv"]
    bob_id = s["bob"]
    tenant_id = s["tenant"]
    headers_bob = auth_headers(s, "bob")

    # 1. Bob removed from tenant
    conn.execute(
        "UPDATE tenant_members SET removed_at = now() WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, bob_id),
    )
    conn.commit()

    # GET /messages returns 403
    r_msg = client.get(f"/v1/conversations/{conv_id}/messages", headers=headers_bob)
    assert r_msg.status_code == 403
    assert "not active" in r_msg.json()["detail"]

    # GET /sync/conversations excludes conv_id
    r_sync = client.get("/v1/sync/conversations", headers=headers_bob)
    assert r_sync.status_code == 200
    conv_ids = [c["conversation_id"] for c in r_sync.json()["conversations"]]
    assert str(conv_id) not in conv_ids

    # 2. Reset removed_at, but mark Bob's user status as suspended
    conn.execute(
        "UPDATE tenant_members SET removed_at = NULL WHERE tenant_id = %s AND user_id = %s",
        (tenant_id, bob_id),
    )
    conn.execute(
        "UPDATE users SET status = 'suspended' WHERE id = %s",
        (bob_id,),
    )
    conn.commit()

    # GET /messages returns 403
    r_msg_susp = client.get(f"/v1/conversations/{conv_id}/messages", headers=headers_bob)
    assert r_msg_susp.status_code == 403
    assert "not active" in r_msg_susp.json()["detail"]

    # GET /sync/conversations excludes conv_id
    r_sync_susp = client.get("/v1/sync/conversations", headers=headers_bob)
    assert r_sync_susp.status_code == 200
    conv_ids_susp = [c["conversation_id"] for c in r_sync_susp.json()["conversations"]]
    assert str(conv_id) not in conv_ids_susp


def test_revoke_device_cross_tenant_admin_and_missing_device_returns_404(conn):
    """Tenant admin cannot revoke a device belonging to another tenant or a missing device ID (returns 404)."""
    s_a = seed_chat(conn)
    s_b = seed_chat(conn)

    admin_a = s_a["alice"]
    bob_a = s_a["bob"]
    carol_a = s_a["carol"]
    tenant_a = s_a["tenant"]

    bob_b = s_b["bob"]

    # Make alice_a a tenant admin of tenant_a
    conn.execute(
        "UPDATE tenant_members SET role = 'admin' WHERE tenant_id = %s AND user_id = %s",
        (tenant_a, admin_a),
    )

    bob_a_device = uuid4()
    bob_b_device = uuid4()
    carol_a_device = uuid4()

    for dev_id, uid in (
        (bob_a_device, bob_a),
        (bob_b_device, bob_b),
        (carol_a_device, carol_a),
    ):
        conn.execute(
            "INSERT INTO devices (id, user_id, platform, push_token, refresh_hash, refresh_family) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (dev_id, uid, "android", f"push_{dev_id}", b"hash", uuid4()),
        )

    # Remove carol_a from tenant_a
    conn.execute(
        "UPDATE tenant_members SET removed_at = now() WHERE tenant_id = %s AND user_id = %s",
        (tenant_a, carol_a),
    )
    conn.commit()

    headers_admin_a = auth_headers(s_a, "alice")

    # 1. Admin of Tenant A attempts to revoke a device owned by user in Tenant B -> 404
    r_cross = client.post(f"/v1/devices/{bob_b_device}/revoke", headers=headers_admin_a)
    assert r_cross.status_code == 404
    revoked_at_b = conn.execute(
        "SELECT revoked_at FROM devices WHERE id = %s", (bob_b_device,)
    ).fetchone()[0]
    assert revoked_at_b is None

    # 2. Admin of Tenant A attempts to revoke a non-existent device ID -> 404
    r_missing = client.post(f"/v1/devices/{uuid4()}/revoke", headers=headers_admin_a)
    assert r_missing.status_code == 404

    # 3. Admin of Tenant A attempts to revoke a device of a removed tenant member -> 404
    r_removed = client.post(f"/v1/devices/{carol_a_device}/revoke", headers=headers_admin_a)
    assert r_removed.status_code == 404

    # 4. Admin of Tenant A revokes a device of an active member in Tenant A -> 200 OK
    r_same = client.post(f"/v1/devices/{bob_a_device}/revoke", headers=headers_admin_a)
    assert r_same.status_code == 200
    assert r_same.json()["revoked"] is True
    revoked_at_a = conn.execute(
        "SELECT revoked_at FROM devices WHERE id = %s", (bob_a_device,)
    ).fetchone()[0]
    assert revoked_at_a is not None
