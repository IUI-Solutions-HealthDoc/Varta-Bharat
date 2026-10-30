"""Security conformance test suite verifying rejection of unauthenticated users and IDOR attacks.

Covers:
1. redeem_ws_ticket:
   - Arbitrary string of 16+ characters is rejected.
   - test:<user_id>:<tenant_id> is rejected outside ENVIRONMENT=local.
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
3. get_current_user dev authentication stub:
   - App refuses to start outside ENVIRONMENT=local (RuntimeError on lifespan startup).
   - get_current_user raises 401 Unauthorized outside ENVIRONMENT=local.
   - In ENVIRONMENT=local, dev stub works with default user, Bearer <uuid>, and X-User-Id.
"""

from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.main import app
from app.messaging.router import get_current_user
from app.ws.router import redeem_ws_ticket
from tests.helpers import seed_chat

client = TestClient(app)


@pytest.fixture(autouse=True)
def use_test_db(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)


# =============================================================================
# 1. WebSocket Ticket Security Tests
# =============================================================================


def test_redeem_ws_ticket_rejects_arbitrary_16_char_ticket():
    """Any arbitrary ticket >= 16 characters or wstk_ format without Valkey entry is rejected."""
    # Arbitrary strings must be rejected
    assert redeem_ws_ticket("a" * 16) is None
    assert redeem_ws_ticket("wstk_randomstring1234567890") is None
    assert redeem_ws_ticket("random_ticket_not_in_valkey") is None

    # Connecting over WebSocket with arbitrary ticket receives INVALID_TICKET error
    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"type": "hello", "ticket": "arbitrary_long_ticket_123456"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "INVALID_TICKET"


def test_redeem_ws_ticket_rejects_dev_ticket_outside_local(monkeypatch):
    """Dev tickets (test:<user>:<tenant>) are strictly rejected outside ENVIRONMENT=local."""
    uid = uuid4()
    tid = uuid4()
    dev_ticket = f"test:{uid}:{tid}"

    # In local environment, dev tickets work
    monkeypatch.setattr(settings, "environment", "local")
    user_local = redeem_ws_ticket(dev_ticket)
    assert user_local is not None
    assert user_local.id == uid

    # In production or staging, dev tickets are rejected
    for env in ("production", "staging", "testing"):
        monkeypatch.setattr(settings, "environment", env)
        assert redeem_ws_ticket(dev_ticket) is None

        # Connecting over WebSocket is rejected with INVALID_TICKET
        with client.websocket_connect("/v1/ws") as ws:
            ws.send_json({"type": "hello", "ticket": dev_ticket})
            err = ws.receive_json()
            assert err["type"] == "error"
            assert err["code"] == "INVALID_TICKET"


def test_ws_ticket_valkey_lifecycle_and_single_use(conn):
    """Tickets issued via POST /v1/ws-ticket pass, and cannot be reused (single-use Plan D-5)."""
    s = seed_chat(conn)
    bob_id = s["bob"]
    tenant_id = s["tenant"]
    headers = {
        "Authorization": f"Bearer {bob_id}",
        "X-Tenant-Id": str(tenant_id),
    }

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
    alice_id = s["alice"]
    carol_id = s["carol"]  # Carol is in tenant but NOT in conv_id
    ticket_carol = f"test:{carol_id}:{s['tenant']}"

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
            headers={"Authorization": f"Bearer {alice_id}"},
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
    ticket_bob = f"test:{bob_id}:{s['tenant']}"

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
    ticket_bob = f"test:{bob_id}:{tenant_id}"

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
    ticket_bob = f"test:{bob_id}:{s['tenant']}"

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
    carol_id = s["carol"]  # Carol not in conv_id
    ticket_carol = f"test:{carol_id}:{s['tenant']}"

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
    bob_id = s["bob"]
    carol_id = s["carol"]
    ticket_bob = f"test:{bob_id}:{s['tenant']}"
    ticket_carol = f"test:{carol_id}:{s['tenant']}"

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
# 3. get_current_user Stub & Environment Security Tests
# =============================================================================


def test_app_refuses_to_start_outside_local_environment(monkeypatch):
    """FastAPI application refuses to start outside ENVIRONMENT=local until BE-2 lands."""
    for non_local_env in ("production", "staging", "testing"):
        monkeypatch.setattr(settings, "environment", non_local_env)

        with pytest.raises(RuntimeError, match="Refusing to start with dev authentication stub"):
            with TestClient(app):
                pass


def test_get_current_user_rejects_outside_local_environment(monkeypatch):
    """Direct invocation or endpoint access to get_current_user outside local raises 401."""
    monkeypatch.setattr(settings, "environment", "production")

    # Direct invocation raises HTTPException 401
    with pytest.raises(HTTPException) as exc_info:
        get_current_user()
    assert exc_info.value.status_code == 401
    assert "ENVIRONMENT=local" in exc_info.value.detail

    # Endpoint calling get_current_user receives 401
    resp = client.get("/v1/sync/conversations")
    assert resp.status_code == 401
    assert "ENVIRONMENT=local" in resp.json()["detail"]


def test_get_current_user_works_in_local_environment(monkeypatch):
    """In ENVIRONMENT=local, dev stub returns default user or honors Bearer and X-User-Id."""
    monkeypatch.setattr(settings, "environment", "local")

    # 1. No header -> default user
    user_default = get_current_user()
    assert user_default.id == UUID("0192df78-0000-7000-8000-000000000001")

    # 2. Bearer <uuid> -> uses uuid
    custom_uid = uuid4()
    user_bearer = get_current_user(authorization=f"Bearer {custom_uid}")
    assert user_bearer.id == custom_uid

    # 3. X-User-Id -> uses uuid
    custom_uid_2 = uuid4()
    user_header = get_current_user(x_user_id=str(custom_uid_2))
    assert user_header.id == custom_uid_2
