"""WebSocket Gateway router (BE-1: P1 Realtime Engine).

Handles the /v1/ws connection lifecycle:
- Handshake: Expects 'hello' frame with ticket (redeem_ws_ticket).
- Welcome: Responds with 'welcome' frame (heartbeat_s=25).
- Pub/Sub: Subscribes to conversation channels via Valkey and broadcasts real-time messages.
- Outgoing: Sends 'msg' frame if <= 4 KB, or 'msg_hint' frame if > 4 KB.
- Incoming: Handles 'ack' frames, enforces monotonic cursors (read_seq <= delivered_seq),
  and broadcasts 'receipt' frames to participants.
- Termination: Clean shutdown and connection cleanup.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
import secrets
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
_conversation_subscribers: dict[UUID, set[WebSocket]] = defaultdict(set)
_device_sockets: dict[UUID, set[WebSocket]] = defaultdict(set)
_lock = asyncio.Lock()

# Background Valkey Pub/Sub subscriber state
_valkey_sub_task: asyncio.Task | None = None
_valkey_subscribed_event: asyncio.Event | None = None


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


async def broadcast_to_conversation(
    conversation_id: UUID, message_json: str, exclude_ws: WebSocket | None = None
) -> None:
    """Broadcast an outgoing frame to active WebSocket connections in a conversation."""
    async with _lock:
        sockets = [
            ws for ws in _conversation_subscribers.get(conversation_id, set()) if ws != exclude_ws
        ]

    for ws in sockets:
        try:
            await ws.send_text(message_json)
        except Exception as exc:  # noqa: BLE001
            log.debug("Failed sending to socket: %s", exc)


async def revoke_device_session(
    device_id: UUID, reason: str = "Device session revoked by security policy"
) -> bool:
    """Send 'revoked' frame to all active sockets of the given device and terminate with code 1008 (P2)."""
    async with _lock:
        sockets = list(_device_sockets.get(device_id, set()))

    if not sockets:
        return False

    frame = RevokedFrame(reason=reason)
    frame_json = frame.model_dump_json()
    for ws in sockets:
        try:
            await ws.send_text(frame_json)
            await ws.close(code=1008)
        except Exception as exc:  # noqa: BLE001
            log.debug("Failed closing revoked device socket: %s", exc)
    return True


def revoke_device_session_sync(
    device_id: UUID, reason: str = "Device session revoked by security policy"
) -> bool:
    """Synchronous helper for Member 2 auth or tests to invoke device revocation."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(revoke_device_session(device_id, reason))
        return True
    except RuntimeError:
        return asyncio.run(revoke_device_session(device_id, reason))


@router.post(
    "/devices/{device_id}/revoke",
    status_code=status.HTTP_200_OK,
    summary="Revoke device session (Member 2 hook / P2)",
    description="Pushes a 'revoked' frame to the active device WebSocket connection and terminates it.",
)
async def revoke_device_endpoint(
    device_id: UUID, reason: str = "Device session revoked by security policy"
) -> dict:
    revoked = await revoke_device_session(device_id, reason)
    return {"revoked": revoked, "device_id": str(device_id)}


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
    """Direct broadcast to in-process sockets (fallback if Valkey is down)."""
    body_bytes = body.encode("utf-8") if body else b""

    if len(body_bytes) <= 4096:
        frame = MsgFrame(
            conversation_id=conversation_id,
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
            conversation_id=conversation_id,
            seq=seq,
            id=message_id,
            sender_id=sender_id,
            kind=kind,
            created_at=created_at,
        )

    frame_json = frame.model_dump_json()

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_to_conversation(conversation_id, frame_json))
    except RuntimeError:
        asyncio.run(broadcast_to_conversation(conversation_id, frame_json))


async def _handle_valkey_message(data_str: str | None) -> None:
    """Deliver a message received from Valkey conv:{id} to local connected WebSockets."""
    if not data_str:
        return
    try:
        data = json.loads(data_str)
        if not isinstance(data, dict):
            return

        conv_id_str = data.get("conversation_id")
        if not conv_id_str:
            return
        conv_id = UUID(conv_id_str)

        async with _lock:
            has_subscribers = bool(_conversation_subscribers.get(conv_id))
        if not has_subscribers:
            return

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

        await broadcast_to_conversation(conv_id, frame.model_dump_json())
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed processing Valkey realtime frame: %s", exc)


async def _valkey_subscriber_loop() -> None:
    """Background task listening on Valkey conv:* channel and fanning out to local WebSockets (plan section 6)."""
    import valkey.asyncio as valkey_async

    while True:
        ps = None
        client = None
        try:
            url = settings.valkey_url
            if url.startswith("redis://"):
                url = "valkey://" + url.removeprefix("redis://")
            client = valkey_async.from_url(url, decode_responses=True)
            ps = client.pubsub()
            await ps.psubscribe("conv:*")
            if _valkey_subscribed_event is not None:
                _valkey_subscribed_event.set()

            async for msg in ps.listen():
                if msg.get("type") == "pmessage":
                    await _handle_valkey_message(msg.get("data"))
        except asyncio.CancelledError:
            break
        except Exception as exc:  # noqa: BLE001
            log.warning("Valkey pubsub subscriber connection error: %s; reconnecting...", exc)
            await asyncio.sleep(1)
        finally:
            if ps is not None:
                try:
                    await ps.aclose()
                except Exception:
                    pass
            if client is not None:
                try:
                    await client.aclose()
                except Exception:
                    pass


async def ensure_valkey_subscriber() -> None:
    """Ensure the Valkey pub/sub fan-out task is running."""
    global _valkey_sub_task, _valkey_subscribed_event
    if _valkey_sub_task is None or _valkey_sub_task.done():
        _valkey_subscribed_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        _valkey_sub_task = loop.create_task(_valkey_subscriber_loop())
        try:
            await asyncio.wait_for(_valkey_subscribed_event.wait(), timeout=1.0)
        except (TimeoutError, Exception) as exc:
            log.debug("Valkey subscriber initial wait timed out: %s", exc)


async def stop_valkey_subscriber() -> None:
    """Cancel the Valkey subscriber task on shutdown."""
    global _valkey_sub_task
    if _valkey_sub_task and not _valkey_sub_task.done():
        _valkey_sub_task.cancel()
        try:
            await _valkey_sub_task
        except asyncio.CancelledError:
            pass
        _valkey_sub_task = None


@router.websocket("/ws")
async def websocket_gateway(websocket: WebSocket) -> None:
    """WebSocket gateway endpoint for real-time messaging, acks, and receipts."""
    await websocket.accept()

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
            message="Initial frame must be 'hello' with a valid ticket.",
        )
        await websocket.send_text(err.model_dump_json())
        await websocket.close(code=1008)
        return

    ticket = data["ticket"]
    user = redeem_ws_ticket(ticket)
    if user is None:
        err = ErrorFrame(code="INVALID_TICKET", message="Invalid or expired ticket.")
        await websocket.send_text(err.model_dump_json())
        await websocket.close(code=1008)
        return

    # Ensure Valkey pub/sub fan-out listener is running
    await ensure_valkey_subscriber()

    # Step 2: Welcome Frame
    welcome = WelcomeFrame(
        heartbeat_s=25,
        user_id=user.id,
        device_id=user.device_id,
    )
    await websocket.send_text(welcome.model_dump_json())

    # Step 3: Discover active conversations and subscribe
    subscribed_convs: set[UUID] = set()
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
                (user.id,),
            ).fetchall()
            subscribed_convs = {r[0] for r in rows}
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not load initial conversation subscriptions: %s", exc)

    async with _lock:
        _device_sockets[user.device_id].add(websocket)
        for cid in subscribed_convs:
            _conversation_subscribers[cid].add(websocket)

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

                # Check active conversation membership before subscribing or acking
                if ack.conversation_id not in subscribed_convs:
                    if not check_active_conversation_membership(user.id, ack.conversation_id):
                        err = ErrorFrame(
                            code="FORBIDDEN",
                            message="Not an active member of conversation",
                        )
                        await websocket.send_text(err.model_dump_json())
                        continue
                    subscribed_convs.add(ack.conversation_id)

                # Ensure socket is subscribed to this conversation
                async with _lock:
                    _conversation_subscribers[ack.conversation_id].add(websocket)

                # Monotonically update cursors in database
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
                            (ack.delivered_seq, ack.read_seq, ack.conversation_id, user.id),
                        ).fetchone()

                        if res is not None:
                            up_del, up_read = res[0], res[1]
                            receipt = ReceiptFrame(
                                conversation_id=ack.conversation_id,
                                user_id=user.id,
                                delivered_seq=up_del,
                                read_seq=up_read,
                            )
                            # Broadcast receipt frame to conversation participants
                            await broadcast_to_conversation(
                                ack.conversation_id, receipt.model_dump_json()
                            )
                except Exception as exc:  # noqa: BLE001
                    log.warning("Failed updating ack cursors: %s", exc)

            elif frame_type == "typing":
                try:
                    typing_in = TypingFrame.model_validate(frame_data)
                except Exception as exc:  # noqa: BLE001
                    err = ErrorFrame(code="MALFORMED_TYPING", message=str(exc))
                    await websocket.send_text(err.model_dump_json())
                    continue

                # Check active conversation membership before subscribing or broadcasting typing
                if typing_in.conversation_id not in subscribed_convs:
                    if not check_active_conversation_membership(user.id, typing_in.conversation_id):
                        err = ErrorFrame(
                            code="FORBIDDEN",
                            message="Not an active member of conversation",
                        )
                        await websocket.send_text(err.model_dump_json())
                        continue
                    subscribed_convs.add(typing_in.conversation_id)

                # Ensure socket is subscribed
                async with _lock:
                    _conversation_subscribers[typing_in.conversation_id].add(websocket)

                typing_out = TypingFrame(
                    conversation_id=typing_in.conversation_id,
                    user_id=user.id,
                    is_typing=typing_in.is_typing,
                )
                await broadcast_to_conversation(
                    typing_in.conversation_id,
                    typing_out.model_dump_json(),
                    exclude_ws=websocket,
                )

            elif frame_type == "subscribe":
                try:
                    sub = SubscribeFrame.model_validate(frame_data)
                except Exception as exc:  # noqa: BLE001
                    err = ErrorFrame(code="MALFORMED_SUBSCRIBE", message=str(exc))
                    await websocket.send_text(err.model_dump_json())
                    continue

                # Check active conversation membership before subscribing
                if sub.conversation_id not in subscribed_convs:
                    if not check_active_conversation_membership(user.id, sub.conversation_id):
                        err = ErrorFrame(
                            code="FORBIDDEN",
                            message="Not an active member of conversation",
                        )
                        await websocket.send_text(err.model_dump_json())
                        continue
                    subscribed_convs.add(sub.conversation_id)

                async with _lock:
                    _conversation_subscribers[sub.conversation_id].add(websocket)
            else:
                # Working rule: safely ignore unknown frame types
                log.debug("Ignored unknown frame type: %s", frame_type)

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup subscriptions on disconnect
        async with _lock:
            _device_sockets[user.device_id].discard(websocket)
            if not _device_sockets[user.device_id]:
                _device_sockets.pop(user.device_id, None)

            for cid in list(_conversation_subscribers.keys()):
                _conversation_subscribers[cid].discard(websocket)
                if not _conversation_subscribers[cid]:
                    _conversation_subscribers.pop(cid, None)
