"""Protocol conformance and stub endpoint tests (BE-1: P0).

Verifies that REST messaging endpoints, WebSocket gateway frames, and OpenAPI schemas
conform strictly to docs/protocol.md and Plan v2 sections 7.2 - 7.4.
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_send_text_message_success():
    conv_id = uuid4()
    cmid = uuid4()
    payload = {
        "client_msg_id": str(cmid),
        "kind": "text",
        "body": "Namaste Bharat!",
    }
    resp = client.post(f"/v1/conversations/{conv_id}/messages", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["seq"] >= 1
    assert "id" in data
    assert "created_at" in data
    assert data["duplicate"] is False


def test_send_media_message_success():
    conv_id = uuid4()
    cmid = uuid4()
    att_id = uuid4()
    payload = {
        "client_msg_id": str(cmid),
        "kind": "media",
        "attachment_id": str(att_id),
    }
    resp = client.post(f"/v1/conversations/{conv_id}/messages", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["seq"] >= 1


def test_send_text_message_rejects_empty_body():
    conv_id = uuid4()
    payload = {
        "client_msg_id": str(uuid4()),
        "kind": "text",
        "body": "   ",
    }
    resp = client.post(f"/v1/conversations/{conv_id}/messages", json=payload)
    assert resp.status_code == 422


def test_send_media_message_rejects_missing_attachment():
    conv_id = uuid4()
    payload = {
        "client_msg_id": str(uuid4()),
        "kind": "media",
    }
    resp = client.post(f"/v1/conversations/{conv_id}/messages", json=payload)
    assert resp.status_code == 422


def test_sync_conversations_endpoint():
    resp = client.get("/v1/sync/conversations")
    assert resp.status_code == 200
    data = resp.json()
    assert "conversations" in data
    assert len(data["conversations"]) >= 1
    item = data["conversations"][0]
    assert "conversation_id" in item
    assert "last_seq" in item
    assert "delivered_seq" in item
    assert "read_seq" in item
    assert "visible_from_seq" in item
    assert item["read_seq"] <= item["delivered_seq"]


def test_get_messages_endpoint():
    conv_id = uuid4()
    resp = client.get(f"/v1/conversations/{conv_id}/messages?after=5&limit=20")
    assert resp.status_code == 200
    data = resp.json()
    assert "messages" in data
    assert "has_more" in data
    assert "last_seq" in data
    assert len(data["messages"]) >= 1
    msg = data["messages"][0]
    assert msg["conversation_id"] == str(conv_id)
    assert msg["seq"] == 6


def test_websocket_handshake_welcome_and_ping():
    with client.websocket_connect("/v1/ws") as ws:
        # Send initial hello frame
        ws.send_json({"type": "hello", "ticket": "test_ticket_123"})

        # Receive welcome frame
        welcome = ws.receive_json()
        assert welcome["type"] == "welcome"
        assert welcome["heartbeat_s"] == 25
        assert "user_id" in welcome
        assert "device_id" in welcome

        # Send ack frame (must not crash)
        ws.send_json({
            "type": "ack",
            "conversation_id": str(uuid4()),
            "delivered_seq": 10,
            "read_seq": 10,
        })

        # Send ping, expect pong
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"

        # Send unknown frame (must be ignored safely)
        ws.send_json({"type": "unknown_future_frame", "foo": "bar"})


def test_websocket_rejects_invalid_handshake():
    with client.websocket_connect("/v1/ws") as ws:
        # Send bad frame instead of hello
        ws.send_json({"type": "not_hello"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert err["code"] == "INVALID_HANDSHAKE"


def test_openapi_contains_messaging_schemas():
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    paths = schema.get("paths", {})
    assert "/v1/conversations/{conversation_id}/messages" in paths
    assert "/v1/sync/conversations" in paths
