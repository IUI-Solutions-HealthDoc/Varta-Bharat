"""Protocol conformance and integration test suite (BE-1: P1 Core Engine).

Verifies:
- POST /v1/conversations/{id}/messages (send, idempotent retries, gapless sequence).
- GET /v1/sync/conversations (active memberships, sync cursors).
- GET /v1/conversations/{id}/messages (visibility, pagination, left_at rejection I4).
- WebSocket Gateway /v1/ws (handshake, welcome, realtime msg <=4KB, hint >4KB, acks, receipts).
- 2 clients sending and receiving in real time.
- Reconnection with gapless sync catch-up.
- Cursor monotonicity and invalid ack rejection.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from app.config import settings
from app.main import app
from tests.helpers import seed_chat

client = TestClient(app)


@pytest.fixture(autouse=True)
def use_test_db(db_url, monkeypatch):
    monkeypatch.setattr(settings, "database_url", db_url)



def test_rest_post_message_and_idempotent_retry(conn):
    s = seed_chat(conn)
    conv_id = s["conv"]
    alice_id = s["alice"]
    headers = {"Authorization": f"Bearer {alice_id}"}
    cmid = uuid4()

    # 1. Send first message
    payload = {
        "client_msg_id": str(cmid),
        "kind": "text",
        "body": "First message from Alice",
    }
    r1 = client.post(f"/v1/conversations/{conv_id}/messages", json=payload, headers=headers)
    assert r1.status_code == 201
    d1 = r1.json()
    assert d1["seq"] == 1
    assert d1["duplicate"] is False

    # 2. Idempotent retry with same client_msg_id returns original
    r2 = client.post(f"/v1/conversations/{conv_id}/messages", json=payload, headers=headers)
    assert r2.status_code == 201
    d2 = r2.json()
    assert d2["seq"] == 1
    assert d2["id"] == d1["id"]
    assert d2["duplicate"] is True

    # 3. Next message gets gapless seq 2
    r3 = client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"client_msg_id": str(uuid4()), "kind": "text", "body": "Second message"},
        headers=headers,
    )
    assert r3.status_code == 201
    assert r3.json()["seq"] == 2


def test_rest_sync_conversations_with_active_memberships(conn):
    s = seed_chat(conn)
    headers = {"Authorization": f"Bearer {s['alice']}"}

    resp = client.get("/v1/sync/conversations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "conversations" in data
    convs = {c["conversation_id"]: c for c in data["conversations"]}
    assert str(s["conv"]) in convs
    item = convs[str(s["conv"])]
    assert item["last_seq"] == 0
    assert item["delivered_seq"] == 0
    assert item["read_seq"] == 0
    assert item["visible_from_seq"] == 1


def test_rest_get_messages_respects_visibility_and_left_members(conn):
    s = seed_chat(conn)
    conv_id = s["conv"]
    headers_alice = {"Authorization": f"Bearer {s['alice']}"}
    headers_bob = {"Authorization": f"Bearer {s['bob']}"}
    headers_carol = {"Authorization": f"Bearer {s['carol']}"}

    # Alice posts 3 messages (seq 1, 2, 3)
    for i in range(1, 4):
        client.post(
            f"/v1/conversations/{conv_id}/messages",
            json={"client_msg_id": str(uuid4()), "kind": "text", "body": f"m{i}"},
            headers=headers_alice,
        )

    # Carol (not a member) gets 403
    r_carol = client.get(f"/v1/conversations/{conv_id}/messages", headers=headers_carol)
    assert r_carol.status_code == 403

    # Bob sets visible_from_seq = 2
    conn.execute(
        "UPDATE conversation_members SET visible_from_seq = 2 WHERE conversation_id = %s AND user_id = %s",
        (conv_id, s["bob"]),
    )
    conn.commit()

    r_bob = client.get(f"/v1/conversations/{conv_id}/messages?after=0", headers=headers_bob)
    assert r_bob.status_code == 200
    msgs = r_bob.json()["messages"]
    # Invariant I4: Bob cannot see seq 1 (only seq >= 2)
    assert [m["seq"] for m in msgs] == [2, 3]

    # Bob leaves the conversation (left_at IS NOT NULL) -> Invariant I4: gets 403
    conn.execute(
        "UPDATE conversation_members SET left_at = now() WHERE conversation_id = %s AND user_id = %s",
        (conv_id, s["bob"]),
    )
    conn.commit()

    r_left = client.get(f"/v1/conversations/{conv_id}/messages", headers=headers_bob)
    assert r_left.status_code == 403


def test_realtime_two_clients_send_and_receive(conn):
    s = seed_chat(conn)
    conv_id = s["conv"]
    bob_ticket = f"test:{s['bob']}:{s['tenant']}"
    headers_alice = {"Authorization": f"Bearer {s['alice']}"}

    with client.websocket_connect("/v1/ws") as ws_bob:
        # Handshake: Bob sends hello frame with ticket
        ws_bob.send_json({"type": "hello", "ticket": bob_ticket})
        welcome = ws_bob.receive_json()
        assert welcome["type"] == "welcome"
        assert welcome["heartbeat_s"] == 25
        assert welcome["user_id"] == str(s["bob"])

        # Alice sends a message via REST
        msg_body = "Hello Bob in real-time!"
        cmid = uuid4()
        r = client.post(
            f"/v1/conversations/{conv_id}/messages",
            json={"client_msg_id": str(cmid), "kind": "text", "body": msg_body},
            headers=headers_alice,
        )
        assert r.status_code == 201
        sent_data = r.json()

        # Bob receives 'msg' frame over WebSocket in real time!
        ws_msg = ws_bob.receive_json()
        assert ws_msg["type"] == "msg"
        assert ws_msg["conversation_id"] == str(conv_id)
        assert ws_msg["seq"] == sent_data["seq"]
        assert ws_msg["body"] == msg_body
        assert ws_msg["sender_id"] == str(s["alice"])


def test_realtime_large_message_receives_hint_and_fetches_via_rest(conn):
    s = seed_chat(conn)
    conv_id = s["conv"]
    bob_ticket = f"test:{s['bob']}:{s['tenant']}"
    headers_alice = {"Authorization": f"Bearer {s['alice']}"}
    headers_bob = {"Authorization": f"Bearer {s['bob']}"}

    with client.websocket_connect("/v1/ws") as ws_bob:
        ws_bob.send_json({"type": "hello", "ticket": bob_ticket})
        assert ws_bob.receive_json()["type"] == "welcome"

        # Alice sends large message (> 4 KB, e.g. 5000 characters)
        large_body = "Varta Bharat " * 400  # ~5200 bytes
        r = client.post(
            f"/v1/conversations/{conv_id}/messages",
            json={"client_msg_id": str(uuid4()), "kind": "text", "body": large_body},
            headers=headers_alice,
        )
        assert r.status_code == 201
        seq = r.json()["seq"]

        # Bob receives lightweight 'msg_hint' frame (Invariant I5)
        hint = ws_bob.receive_json()
        assert hint["type"] == "msg_hint"
        assert hint["conversation_id"] == str(conv_id)
        assert hint["seq"] == seq

        # Bob fetches full body via REST
        fetch_r = client.get(
            f"/v1/conversations/{conv_id}/messages?after={seq - 1}&limit=1", headers=headers_bob
        )
        assert fetch_r.status_code == 200
        fetched_msgs = fetch_r.json()["messages"]
        assert len(fetched_msgs) == 1
        assert fetched_msgs[0]["body"] == large_body


def test_offline_client_reconnect_gapless_sync(conn):
    s = seed_chat(conn)
    conv_id = s["conv"]
    headers_alice = {"Authorization": f"Bearer {s['alice']}"}
    headers_bob = {"Authorization": f"Bearer {s['bob']}"}

    # Alice sends 3 messages while Bob is offline
    for i in range(1, 4):
        client.post(
            f"/v1/conversations/{conv_id}/messages",
            json={"client_msg_id": str(uuid4()), "kind": "text", "body": f"offline msg {i}"},
            headers=headers_alice,
        )

    # Bob reconnects:
    # Step 1: Connect WebSocket
    with client.websocket_connect("/v1/ws") as ws_bob:
        ws_bob.send_json({"type": "hello", "ticket": f"test:{s['bob']}:{s['tenant']}"})
        assert ws_bob.receive_json()["type"] == "welcome"

        # Step 2: Sync active conversations to discover latest server sequence
        sync_r = client.get("/v1/sync/conversations", headers=headers_bob)
        assert sync_r.status_code == 200
        conv_info = [
            c for c in sync_r.json()["conversations"] if c["conversation_id"] == str(conv_id)
        ][0]
        assert conv_info["last_seq"] == 3

        # Step 3: Catch-up fetch all messages after local highest (0)
        fetch_r = client.get(
            f"/v1/conversations/{conv_id}/messages?after=0&limit=50", headers=headers_bob
        )
        assert fetch_r.status_code == 200
        msgs = fetch_r.json()["messages"]
        assert [m["seq"] for m in msgs] == [1, 2, 3]

        # Step 4: Bob sends ack advancing cursors
        ws_bob.send_json({
            "type": "ack",
            "conversation_id": str(conv_id),
            "delivered_seq": 3,
            "read_seq": 3,
        })


def test_ack_frame_advances_cursors_monotonically_and_broadcasts_receipt(conn):
    s = seed_chat(conn)
    conv_id = s["conv"]
    bob_ticket = f"test:{s['bob']}:{s['tenant']}"

    with client.websocket_connect("/v1/ws") as ws_bob:
        ws_bob.send_json({"type": "hello", "ticket": bob_ticket})
        assert ws_bob.receive_json()["type"] == "welcome"

        # Invalid ack: read_seq > delivered_seq rejected
        ws_bob.send_json({
            "type": "ack",
            "conversation_id": str(conv_id),
            "delivered_seq": 2,
            "read_seq": 5,
        })
        err = ws_bob.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "INVALID_ACK"

        # Valid ack: Bob delivers seq 5, reads seq 4
        ws_bob.send_json({
            "type": "ack",
            "conversation_id": str(conv_id),
            "delivered_seq": 5,
            "read_seq": 4,
        })
        receipt = ws_bob.receive_json()
        assert receipt["type"] == "receipt"
        assert receipt["conversation_id"] == str(conv_id)
        assert receipt["user_id"] == str(s["bob"])
        assert receipt["delivered_seq"] == 5
        assert receipt["read_seq"] == 4

        # Verify DB cursors updated
        row = conn.execute(
            "SELECT delivered_seq, read_seq FROM conversation_members "
            "WHERE conversation_id = %s AND user_id = %s",
            (conv_id, s["bob"]),
        ).fetchone()
        assert row == (5, 4)

        # Monotonicity test: Bob sends smaller cursors (delivered 2, read 1)
        ws_bob.send_json({
            "type": "ack",
            "conversation_id": str(conv_id),
            "delivered_seq": 2,
            "read_seq": 1,
        })
        receipt2 = ws_bob.receive_json()
        assert receipt2["type"] == "receipt"

        # DB cursors must remain at 5 and 4 (GREATEST monotonic invariant)
        row2 = conn.execute(
            "SELECT delivered_seq, read_seq FROM conversation_members "
            "WHERE conversation_id = %s AND user_id = %s",
            (conv_id, s["bob"]),
        ).fetchone()
        assert row2 == (5, 4)


def test_message_deletion_tombstone_permissions_and_invariants(conn):
    s = seed_chat(conn)
    conv_id = s["conv"]
    headers_alice = {"Authorization": f"Bearer {s['alice']}"}
    headers_bob = {"Authorization": f"Bearer {s['bob']}"}

    # 1. Alice sends message 1
    r1 = client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"client_msg_id": str(uuid4()), "kind": "text", "body": "Original message"},
        headers=headers_alice,
    )
    assert r1.status_code == 201
    assert r1.json()["seq"] == 1

    # 2. Bob sends message 2
    r2 = client.post(
        f"/v1/conversations/{conv_id}/messages",
        json={"client_msg_id": str(uuid4()), "kind": "text", "body": "Bob message"},
        headers=headers_bob,
    )
    assert r2.status_code == 201
    assert r2.json()["seq"] == 2

    # 3. Bob (non-admin) tries to delete Alice's message 1 -> 403 Forbidden
    del_fail = client.delete(f"/v1/conversations/{conv_id}/messages/1", headers=headers_bob)
    assert del_fail.status_code == 403

    # 4. Deleting non-existent message -> 404
    del_404 = client.delete(f"/v1/conversations/{conv_id}/messages/999", headers=headers_alice)
    assert del_404.status_code == 404

    # 5. Alice deletes her own message 1 -> 200 OK, tombstone seq=3
    del_ok = client.delete(f"/v1/conversations/{conv_id}/messages/1", headers=headers_alice)
    assert del_ok.status_code == 200
    d = del_ok.json()
    assert d["seq"] == 3
    assert d["target_seq"] == 1
    assert d["kind"] == "delete"

    # Invariant I6: Original row is NOT deleted from database
    orig_row = conn.execute(
        "SELECT kind, body FROM messages WHERE conversation_id = %s AND seq = 1",
        (conv_id,),
    ).fetchone()
    assert orig_row == ("text", "Original message")

    # Tombstone row exists with target_seq=1, body=None
    tomb_row = conn.execute(
        "SELECT kind, target_seq, body FROM messages WHERE conversation_id = %s AND seq = 3",
        (conv_id,),
    ).fetchone()
    assert tomb_row == ("delete", 1, None)

    # 6. Alice (conversation admin) can delete Bob's message 2 -> 200 OK, tombstone seq=4
    del_admin = client.delete(f"/v1/conversations/{conv_id}/messages/2", headers=headers_alice)
    assert del_admin.status_code == 200
    assert del_admin.json()["seq"] == 4
    assert del_admin.json()["target_seq"] == 2


def test_ws_typing_indicator(conn):
    s = seed_chat(conn)
    conv_id = s["conv"]
    ticket_alice = f"test:{s['alice']}:{s['tenant']}"
    ticket_bob = f"test:{s['bob']}:{s['tenant']}"

    # Bob connects to listen for typing
    with client.websocket_connect("/v1/ws") as ws_bob:
        ws_bob.send_json({"type": "hello", "ticket": ticket_bob})
        assert ws_bob.receive_json()["type"] == "welcome"

        # Alice connects and emits typing frame
        with client.websocket_connect("/v1/ws") as ws_alice:
            ws_alice.send_json({"type": "hello", "ticket": ticket_alice})
            assert ws_alice.receive_json()["type"] == "welcome"

            ws_alice.send_json({
                "type": "typing",
                "conversation_id": str(conv_id),
                "is_typing": True,
            })

            # Bob receives typing frame with Alice's user_id
            frame = ws_bob.receive_json()
            assert frame["type"] == "typing"
            assert frame["conversation_id"] == str(conv_id)
            assert frame["user_id"] == str(s["alice"])
            assert frame["is_typing"] is True


def test_ws_device_revocation(conn):
    s = seed_chat(conn)
    device_id = uuid4()
    ticket_alice = f"test:{s['alice']}:{s['tenant']}:{device_id}"

    with client.websocket_connect("/v1/ws") as ws:
        ws.send_json({"type": "hello", "ticket": ticket_alice})
        welcome = ws.receive_json()
        assert welcome["type"] == "welcome"
        assert welcome["device_id"] == str(device_id)

        # Trigger device revocation via endpoint
        rev_resp = client.post(
            f"/v1/devices/{device_id}/revoke",
            params={"reason": "Device lost or stolen"},
        )
        assert rev_resp.status_code == 200
        assert rev_resp.json()["revoked"] is True

        # Client receives revoked frame
        rev_frame = ws.receive_json()
        assert rev_frame["type"] == "revoked"
        assert rev_frame["reason"] == "Device lost or stolen"

