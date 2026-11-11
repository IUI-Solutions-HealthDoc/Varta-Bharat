"""WebSocket Gateway router (BE-1: P1 Realtime Engine).

Handles the /v1/ws connection lifecycle:
- Handshake: Expects 'hello' frame with ticket (redeem_ws_ticket).
- Welcome: Responds with 'welcome' frame (heartbeat_s=25).
- Pub/Sub: Subscribes to conversation and device channels via Valkey and broadcasts real-time messages.
- Outgoing: Sends 'msg' frame if <= 4 KB, or 'msg_hint' frame if > 4 KB.
- Incoming: Handles 'ack' frames, enforces monotonic cursors (read_seq <= delivered_seq),
  and broadcasts 'receipt' frames to participants via Valkey.
- Termination: Clean shutdown and connection cleanup.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
import secrets
import threading
import time
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from app.config import settings
from app.core.db import get_conn
from app.core.valkey import get_valkey
from app.messaging.router import AuthUser, get_current_user
from app.ws.schemas import (
    AckFrame,
    ErrorFrame,
    MsgFrame,
    MsgHintFrame,
    ReceiptFrame,
    RevokedFrame,
    SubscribeFrame,
    TypingFrame,
    WelcomeFrame,
    WsTicketResponse,
)

router = APIRouter(prefix="/v1", tags=["realtime"])
log = logging.getLogger("varta.ws")


@dataclass(frozen=True)
class WsUser:
    id: UUID
    tenant_id: UUID
    device_id: UUID


# In-memory registry of active WebSocket connections per conversation and device
_state_lock = threading.Lock()
_conversation_subscribers: dict[UUID, set[WebSocket]] = defaultdict(set)
_device_sockets: dict[UUID, set[WebSocket]] = defaultdict(set)
_socket_user: dict[WebSocket, UUID] = {}
_socket_device: dict[WebSocket, UUID] = {}
_socket_loop: dict[WebSocket, asyncio.AbstractEventLoop] = {}

# Background Valkey Pub/Sub subscriber daemon thread state
_pubsub_thread: threading.Thread | None = None
_pubsub_stop_event = threading.Event()
_pubsub_ready_event = threading.Event()
_thread_init_lock = threading.Lock()


def redeem_ws_ticket(ticket: str) -> WsUser | None:
    """Validate and redeem a single-use WebSocket ticket (Plan D-5 / Member 2 contract)."""
    # 1. Valkey single-use ticket check using shared client
    try:
        client = get_valkey()
        key = f"ws_ticket:{ticket}"
        try:
            raw = client.getdel(key)
        except AttributeError:
            raw = client.get(key)
            if raw:
                client.delete(key)
        if raw:
            data = json.loads(raw)
            return WsUser(
                id=UUID(data["user_id"]),
                tenant_id=UUID(data["tenant_id"]),
                device_id=UUID(data.get("device_id") or str(uuid4())),
            )
    except Exception as exc:  # noqa: BLE001
        log.debug("Valkey ticket lookup failed: %s", exc)

    # 2. Test / Dev ticket format: test:<user_id>:<tenant_id> or test:<user_id>:<tenant_id>:<device_id>
    # Allowed ONLY when settings.environment == "local"
    if settings.environment == "local" and ticket.startswith("test:"):
        parts = ticket.split(":")
        try:
            user_id = UUID(parts[1]) if len(parts) > 1 else uuid4()
            tenant_id = UUID(parts[2]) if len(parts) > 2 else uuid4()
            device_id = UUID(parts[3]) if len(parts) > 3 else uuid4()
            return WsUser(id=user_id, tenant_id=tenant_id, device_id=device_id)
        except (ValueError, IndexError):
            return None

    return None


def check_active_conversation_membership(user_id: UUID, conversation_id: UUID) -> bool:
    """Verify active membership: left_at IS NULL, tenant member not removed, user active."""
    try:
        with get_conn() as conn:
            row = conn.execute(
                """
                SELECT 1
                FROM conversation_members cm
                JOIN conversations c ON c.id = cm.conversation_id
                JOIN tenant_members tm ON tm.tenant_id = c.tenant_id AND tm.user_id = cm.user_id
                JOIN users u ON u.id = cm.user_id
                WHERE cm.conversation_id = %s
                  AND cm.user_id = %s
                  AND cm.left_at IS NULL
                  AND tm.removed_at IS NULL
                  AND u.status = 'active'
                """,
                (conversation_id, user_id),
            ).fetchone()
            return row is not None
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not verify active conversation membership: %s", exc)
        return False


def _get_initial_subscribed_convs(user_id: UUID) -> set[UUID]:
    """Fetch initial active conversation IDs for a user on WebSocket connection."""
    try:
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT cm.conversation_id
                FROM conversation_members cm
                JOIN conversations c ON c.id = cm.conversation_id
                JOIN tenant_members tm ON tm.tenant_id = c.tenant_id AND tm.user_id = cm.user_id
                JOIN users u ON u.id = cm.user_id
                WHERE cm.user_id = %s
                  AND cm.left_at IS NULL
                  AND tm.removed_at IS NULL
                  AND u.status = 'active'
                """,
                (user_id,),
            ).fetchall()
            return {r[0] for r in rows}
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not load initial conversation subscriptions: %s", exc)
        return set()


def _update_ack_cursors(
    conv_id: UUID, user_id: UUID, del_seq: int, r_seq: int
) -> tuple[int, int] | None:
    """Update delivered_seq and read_seq monotonically in database."""
    try:
        with get_conn() as conn:
            res = conn.execute(
                """
                UPDATE conversation_members
                SET delivered_seq = GREATEST(delivered_seq, %s),
                    read_seq = GREATEST(read_seq, %s)
                WHERE conversation_id = %s AND user_id = %s AND left_at IS NULL
                RETURNING delivered_seq, read_seq
                """,
                (del_seq, r_seq, conv_id, user_id),
            ).fetchone()
            if res is not None:
                return (res[0], res[1])
            return None
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed updating ack cursors: %s", exc)
        return None


def publish_valkey_channel(channel: str, payload: dict) -> None:
    """Publish JSON payload to Valkey channel for multi-instance fan-out."""
    try:
        client = get_valkey()
        client.publish(channel, json.dumps(payload))
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed publishing to Valkey channel %s: %s", channel, exc)


@router.post(
    "/ws-ticket",
    response_model=WsTicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Issue WebSocket ticket (Plan D-5)",
    description="Issues a single-use ticket stored in Valkey with a 30s TTL for WebSocket authentication.",
)
def create_ws_ticket_endpoint(
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> WsTicketResponse:
    ticket = f"wstk_{secrets.token_hex(16)}"
    key = f"ws_ticket:{ticket}"
    val = json.dumps(
        {
            "user_id": str(user.id),
            "tenant_id": str(user.tenant_id),
            "device_id": str(user.device_id),
        }
    )

    try:
        client = get_valkey()
        client.set(key, val, ex=30)
    except Exception as exc:
        log.error("Failed storing ticket in Valkey: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Ticket storage service unavailable",
        ) from exc

    return WsTicketResponse(ticket=ticket, expires_in=30)


def _dispatch_to_socket(ws: WebSocket, coro_func, *args) -> None:
    """Thread-safe and cross-loop safe helper to dispatch coroutine to a WebSocket's event loop."""
    with _state_lock:
        target_loop = _socket_loop.get(ws)
    if target_loop is None or not target_loop.is_running():
        return
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if current_loop is target_loop:
        target_loop.create_task(coro_func(*args))
    else:
        asyncio.run_coroutine_threadsafe(coro_func(*args), target_loop)


async def _deliver_conversation_frame(
    ws: WebSocket,
    conversation_id: UUID,
    message_json: str,
    exclude_device: UUID | None = None,
    exclude_ws: WebSocket | None = None,
) -> None:
    if ws == exclude_ws:
        return
    with _state_lock:
        dev_id = _socket_device.get(ws)
        user_id = _socket_user.get(ws)
    if exclude_device is not None and dev_id == exclude_device:
        return
    if user_id is None:
        return

    # Invariant I4: Re-check active membership before delivering live frame
    is_active = await asyncio.to_thread(
        check_active_conversation_membership, user_id, conversation_id
    )
    if not is_active:
        with _state_lock:
            _conversation_subscribers[conversation_id].discard(ws)
        return

    try:
        await ws.send_text(message_json)
    except Exception as exc:  # noqa: BLE001
        log.debug("Failed sending to socket: %s", exc)


def _broadcast_to_conversation_sync(
    conversation_id: UUID,
    message_json: str,
    exclude_device: UUID | None = None,
    exclude_ws: WebSocket | None = None,
) -> None:
    """Broadcast outgoing frame to active WebSocket connections in a conversation."""
    with _state_lock:
        candidate_sockets = list(_conversation_subscribers.get(conversation_id, set()))

    for ws in candidate_sockets:
        _dispatch_to_socket(
            ws,
            _deliver_conversation_frame,
            ws,
            conversation_id,
            message_json,
            exclude_device,
            exclude_ws,
        )


async def broadcast_to_conversation(
    conversation_id: UUID,
    message_json: str,
    exclude_device: UUID | None = None,
    exclude_ws: WebSocket | None = None,
) -> None:
    _broadcast_to_conversation_sync(conversation_id, message_json, exclude_device, exclude_ws)


async def _revoke_and_close_socket(ws: WebSocket, frame_json: str) -> None:
    try:
        await ws.send_text(frame_json)
    except Exception:
        pass
    try:
        await ws.close(code=1008)
    except Exception:
        pass


def _close_revoked_device_sockets(device_id: UUID, reason: str) -> bool:
    """Close all active local sockets belonging to the revoked device."""
    with _state_lock:
        sockets = list(_device_sockets.get(device_id, set()))

    if not sockets:
        return False

    frame = RevokedFrame(reason=reason)
    frame_json = frame.model_dump_json()
    for ws in sockets:
        _dispatch_to_socket(ws, _revoke_and_close_socket, ws, frame_json)
    return True


async def revoke_device_session(
    device_id: UUID, reason: str = "Device session revoked by security policy"
) -> bool:
    """Send 'revoked' frame to all active sockets of the given device and terminate with code 1008 (P2).

    Fans out across instances via Valkey channel device:{device_id}.
    """
    publish_valkey_channel(
        f"device:{device_id}",
        {
            "type": "revoked",
            "device_id": str(device_id),
            "reason": reason,
        },
    )
    return _close_revoked_device_sockets(device_id, reason)


def revoke_device_session_sync(
    device_id: UUID, reason: str = "Device session revoked by security policy"
) -> bool:
    """Synchronous helper for Member 2 auth or tests to invoke device revocation without asyncio.run cross-loop errors."""
    publish_valkey_channel(
        f"device:{device_id}",
        {
            "type": "revoked",
            "device_id": str(device_id),
            "reason": reason,
        },
    )
    return _close_revoked_device_sockets(device_id, reason)


def _check_device_revoke_auth_and_mark(
    d_id: UUID, u_id: UUID, t_id: UUID, u_dev_id: UUID
) -> tuple[bool, bool]:
    """Check if user owns device or is tenant admin, and mark revoked in devices table if present."""
    with get_conn() as conn:
        row = conn.execute("SELECT user_id FROM devices WHERE id = %s", (d_id,)).fetchone()
        if row is not None:
            dev_user_id = row[0]
            if dev_user_id == u_id:
                conn.execute(
                    "UPDATE devices SET revoked_at = now() WHERE id = %s AND revoked_at IS NULL",
                    (d_id,),
                )
                return (True, True)
            # Check tenant admin
            tm = conn.execute(
                "SELECT role FROM tenant_members WHERE tenant_id = %s AND user_id = %s AND removed_at IS NULL",
                (t_id, u_id),
            ).fetchone()
            if tm and tm[0] == "admin":
                conn.execute(
                    "UPDATE devices SET revoked_at = now() WHERE id = %s AND revoked_at IS NULL",
                    (d_id,),
                )
                return (True, True)
            return (False, True)  # Exists but unauthorized
        else:
            # Device not in devices table (e.g. dev session)
            if u_dev_id == d_id:
                return (True, False)
            # Check tenant admin
            tm = conn.execute(
                "SELECT role FROM tenant_members WHERE tenant_id = %s AND user_id = %s AND removed_at IS NULL",
                (t_id, u_id),
            ).fetchone()
            if tm and tm[0] == "admin":
                return (True, False)
            return (False, False)


@router.post(
    "/devices/{device_id}/revoke",
    status_code=status.HTTP_200_OK,
    summary="Revoke device session (Member 2 hook / P2)",
    description="Pushes a 'revoked' frame to the active device WebSocket connection and terminates it.",
)
async def revoke_device_endpoint(
    device_id: UUID,
    user: Annotated[AuthUser, Depends(get_current_user)],
    reason: str = "Device session revoked by security policy",
) -> dict:
    authorized, exists = await asyncio.to_thread(
        _check_device_revoke_auth_and_mark,
        device_id,
        user.id,
        user.tenant_id,
        user.device_id,
    )
    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to revoke this device session",
        )

    await revoke_device_session(device_id, reason)
    return {"revoked": True, "device_id": str(device_id)}


def broadcast_realtime_message(
    conversation_id: UUID,
    seq: int,
    message_id: UUID,
    sender_id: UUID,
    kind: str,
    created_at: datetime,
    body: str | None = None,
    attachment_id: UUID | None = None,
) -> None:
    """Publish realtime message to Valkey channel without cross-loop asyncio.run."""
    body_bytes = body.encode("utf-8") if body else b""
    frame_type = "msg" if (body is not None and len(body_bytes) <= 4096) else "msg_hint"
    payload = {
        "type": frame_type,
        "conversation_id": str(conversation_id),
        "seq": seq,
        "id": str(message_id),
        "sender_id": str(sender_id),
        "kind": kind,
        "created_at": created_at.isoformat(),
    }
    if frame_type == "msg":
        payload["body"] = body
        payload["attachment_id"] = str(attachment_id) if attachment_id else None

    publish_valkey_channel(f"conv:{conversation_id}", payload)


def _handle_valkey_message_sync(channel: str, data_str: str | None) -> None:
    """Deliver a message received from Valkey conv:{id} or device:{id} to local connected WebSockets."""
    if not data_str:
        return
    try:
        data = json.loads(data_str)
        if not isinstance(data, dict):
            return

        msg_type = data.get("type")

        # 1. Device revocation event
        if channel.startswith("device:") or msg_type == "revoked":
            dev_id_str = data.get("device_id")
            if dev_id_str:
                dev_id = UUID(dev_id_str)
                reason = data.get("reason", "Device session revoked by security policy")
                _close_revoked_device_sockets(dev_id, reason)
            return

        # 2. Conversation events (msg, msg_hint, receipt, typing)
        conv_id_str = data.get("conversation_id")
        if not conv_id_str:
            return
        conv_id = UUID(conv_id_str)

        with _state_lock:
            has_subscribers = bool(_conversation_subscribers.get(conv_id))
        if not has_subscribers:
            return

        if msg_type == "receipt":
            receipt = ReceiptFrame(
                conversation_id=conv_id,
                user_id=UUID(data["user_id"]),
                delivered_seq=int(data["delivered_seq"]),
                read_seq=int(data["read_seq"]),
            )
            _broadcast_to_conversation_sync(conv_id, receipt.model_dump_json())
            return

        if msg_type == "typing":
            typing_frame = TypingFrame(
                conversation_id=conv_id,
                user_id=UUID(data["user_id"]),
                is_typing=bool(data["is_typing"]),
            )
            ex_device = UUID(data["device_id"]) if data.get("device_id") else None
            _broadcast_to_conversation_sync(
                conv_id, typing_frame.model_dump_json(), exclude_device=ex_device
            )
            return

        # Regular message or msg_hint
        seq = int(data["seq"])
        message_id = UUID(data["id"])
        sender_id = UUID(data["sender_id"])
        kind = data.get("kind", "text")
        created_at_raw = data.get("created_at")
        created_at = datetime.fromisoformat(created_at_raw) if created_at_raw else datetime.now(UTC)
        body = data.get("body")
        attachment_id = UUID(data["attachment_id"]) if data.get("attachment_id") else None

        body_bytes = body.encode("utf-8") if body is not None else b""
        if body is not None and len(body_bytes) <= 4096:
            frame = MsgFrame(
                conversation_id=conv_id,
                seq=seq,
                id=message_id,
                sender_id=sender_id,
                kind=kind,
                body=body,
                attachment_id=attachment_id,
                created_at=created_at,
            )
        else:
            frame = MsgHintFrame(
                conversation_id=conv_id,
                seq=seq,
                id=message_id,
                sender_id=sender_id,
                kind=kind,
                created_at=created_at,
            )

        _broadcast_to_conversation_sync(conv_id, frame.model_dump_json())
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed processing Valkey realtime frame: %s", exc)


def _valkey_subscriber_worker() -> None:
    """Synchronous worker running in a daemon thread listening on Valkey conv:* and device:* channels."""
    while not _pubsub_stop_event.is_set():
        ps = None
        try:
            client = get_valkey()
            ps = client.pubsub()
            ps.psubscribe("conv:*", "device:*")
            # Wait for both pattern subscription confirmations
            confirmations = 0
            while confirmations < 2 and not _pubsub_stop_event.is_set():
                m = ps.get_message(timeout=1.0)
                if m and m.get("type") == "psubscribe":
                    confirmations = m.get("data", confirmations + 1)
            _pubsub_ready_event.set()

            while not _pubsub_stop_event.is_set():
                msg = ps.get_message(ignore_subscribe_messages=True, timeout=0.5)
                if msg is not None and msg.get("type") == "pmessage":
                    _handle_valkey_message_sync(msg.get("channel", ""), msg.get("data"))
        except Exception as exc:  # noqa: BLE001
            if not _pubsub_stop_event.is_set():
                log.warning("Valkey pubsub worker error: %s; reconnecting in 1s...", exc)
                time.sleep(1)
        finally:
            if ps is not None:
                try:
                    ps.close()
                except Exception:
                    pass


def ensure_valkey_subscriber_thread() -> None:
    """Ensure the background Valkey subscriber daemon thread is running."""
    global _pubsub_thread
    with _thread_init_lock:
        if _pubsub_thread is None or not _pubsub_thread.is_alive():
            _pubsub_stop_event.clear()
            _pubsub_ready_event.clear()
            _pubsub_thread = threading.Thread(
                target=_valkey_subscriber_worker,
                name="ValkeyPubSubWorker",
                daemon=True,
            )
            _pubsub_thread.start()
            _pubsub_ready_event.wait(timeout=2.0)


async def ensure_valkey_subscriber() -> None:
    ensure_valkey_subscriber_thread()


async def stop_valkey_subscriber() -> None:
    _pubsub_stop_event.set()


@router.websocket("/ws")
async def websocket_gateway(websocket: WebSocket) -> None:
    """WebSocket gateway endpoint for real-time messaging, acks, and receipts."""
    ensure_valkey_subscriber_thread()
    await websocket.accept()
    loop = asyncio.get_running_loop()

    # Step 1: Handshake - Expect hello frame with ticket
    try:
        raw_msg = await websocket.receive_text()
        data = json.loads(raw_msg)
    except (WebSocketDisconnect, json.JSONDecodeError):
        await websocket.close(code=1008)
        return

    if not isinstance(data, dict) or data.get("type") != "hello" or not data.get("ticket"):
        err = ErrorFrame(
            code="INVALID_HANDSHAKE",
            message="Expected 'hello' frame with ticket.",
        )
        await websocket.send_text(err.model_dump_json())
        await websocket.close(code=1008)
        return

    user = redeem_ws_ticket(data["ticket"])
    if user is None:
        err = ErrorFrame(code="INVALID_TICKET", message="Invalid or expired ticket.")
        await websocket.send_text(err.model_dump_json())
        await websocket.close(code=1008)
        return

    # Step 2: Discover active conversations and subscribe (offloaded to thread)
    subscribed_convs = await asyncio.to_thread(_get_initial_subscribed_convs, user.id)

    with _state_lock:
        _socket_user[websocket] = user.id
        _socket_device[websocket] = user.device_id
        _socket_loop[websocket] = loop
        _device_sockets[user.device_id].add(websocket)
        for cid in subscribed_convs:
            _conversation_subscribers[cid].add(websocket)

    # Step 3: Welcome Frame
    welcome = WelcomeFrame(
        heartbeat_s=25,
        user_id=user.id,
        device_id=user.device_id,
    )
    await websocket.send_text(welcome.model_dump_json())

    # Step 4: Frame loop
    try:
        while True:
            text = await websocket.receive_text()
            try:
                frame_data = json.loads(text)
            except json.JSONDecodeError:
                continue

            frame_type = frame_data.get("type") if isinstance(frame_data, dict) else None

            if frame_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif frame_type == "ack":
                try:
                    ack = AckFrame.model_validate(frame_data)
                except Exception as exc:  # noqa: BLE001
                    err = ErrorFrame(code="MALFORMED_ACK", message=str(exc))
                    await websocket.send_text(err.model_dump_json())
                    continue

                # Invariant I5: read_seq can never exceed delivered_seq
                if ack.read_seq > ack.delivered_seq:
                    err = ErrorFrame(
                        code="INVALID_ACK",
                        message="read_seq cannot exceed delivered_seq",
                    )
                    await websocket.send_text(err.model_dump_json())
                    continue

                # Check active conversation membership before subscribing or acking (offloaded)
                if ack.conversation_id not in subscribed_convs:
                    is_member = await asyncio.to_thread(
                        check_active_conversation_membership, user.id, ack.conversation_id
                    )
                    if not is_member:
                        err = ErrorFrame(
                            code="FORBIDDEN",
                            message="Not an active member of conversation",
                        )
                        await websocket.send_text(err.model_dump_json())
                        continue
                    subscribed_convs.add(ack.conversation_id)

                with _state_lock:
                    _conversation_subscribers[ack.conversation_id].add(websocket)

                # Monotonically update cursors in database (offloaded to thread)
                res = await asyncio.to_thread(
                    _update_ack_cursors,
                    ack.conversation_id,
                    user.id,
                    ack.delivered_seq,
                    ack.read_seq,
                )
                if res is not None:
                    up_del, up_read = res[0], res[1]
                    publish_valkey_channel(
                        f"conv:{ack.conversation_id}",
                        {
                            "type": "receipt",
                            "conversation_id": str(ack.conversation_id),
                            "user_id": str(user.id),
                            "delivered_seq": up_del,
                            "read_seq": up_read,
                        },
                    )

            elif frame_type == "typing":
                try:
                    typing_in = TypingFrame.model_validate(frame_data)
                except Exception as exc:  # noqa: BLE001
                    err = ErrorFrame(code="MALFORMED_TYPING", message=str(exc))
                    await websocket.send_text(err.model_dump_json())
                    continue

                # Check active conversation membership before subscribing or broadcasting typing (offloaded)
                if typing_in.conversation_id not in subscribed_convs:
                    is_member = await asyncio.to_thread(
                        check_active_conversation_membership, user.id, typing_in.conversation_id
                    )
                    if not is_member:
                        err = ErrorFrame(
                            code="FORBIDDEN",
                            message="Not an active member of conversation",
                        )
                        await websocket.send_text(err.model_dump_json())
                        continue
                    subscribed_convs.add(typing_in.conversation_id)

                with _state_lock:
                    _conversation_subscribers[typing_in.conversation_id].add(websocket)

                # Fan out typing via Valkey channel
                publish_valkey_channel(
                    f"conv:{typing_in.conversation_id}",
                    {
                        "type": "typing",
                        "conversation_id": str(typing_in.conversation_id),
                        "user_id": str(user.id),
                        "device_id": str(user.device_id),
                        "is_typing": typing_in.is_typing,
                    },
                )

            elif frame_type == "subscribe":
                try:
                    sub = SubscribeFrame.model_validate(frame_data)
                except Exception as exc:  # noqa: BLE001
                    err = ErrorFrame(code="MALFORMED_SUBSCRIBE", message=str(exc))
                    await websocket.send_text(err.model_dump_json())
                    continue

                # Check active conversation membership before subscribing (offloaded)
                if sub.conversation_id not in subscribed_convs:
                    is_member = await asyncio.to_thread(
                        check_active_conversation_membership, user.id, sub.conversation_id
                    )
                    if not is_member:
                        err = ErrorFrame(
                            code="FORBIDDEN",
                            message="Not an active member of conversation",
                        )
                        await websocket.send_text(err.model_dump_json())
                        continue
                    subscribed_convs.add(sub.conversation_id)

                with _state_lock:
                    _conversation_subscribers[sub.conversation_id].add(websocket)

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup subscriptions on disconnect
        with _state_lock:
            _socket_user.pop(websocket, None)
            _socket_device.pop(websocket, None)
            _socket_loop.pop(websocket, None)
            _device_sockets[user.device_id].discard(websocket)
            if not _device_sockets[user.device_id]:
                _device_sockets.pop(user.device_id, None)
            for s in _conversation_subscribers.values():
                s.discard(websocket)
