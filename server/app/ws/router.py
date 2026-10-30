"""WebSocket Gateway router (BE-1: P0 Stubs).

Handles the /v1/ws connection lifecycle:
- Handshake: Expects 'hello' frame with ticket.
- Welcome: Responds with 'welcome' frame (heartbeat_s=25).
- Frame processing: Accepts 'ack' frames, safely ignores unknown frames.
- Connection termination: Clean handling of disconnects.
"""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.ws.schemas import ErrorFrame, WelcomeFrame

router = APIRouter(prefix="/v1", tags=["realtime"])
log = logging.getLogger("varta.ws")


@router.websocket("/ws")
async def websocket_gateway(websocket: WebSocket) -> None:
    """WebSocket gateway endpoint for real-time messaging and events."""
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

    # In P1, Member 2's redeem_ws_ticket(ticket) will authenticate the ticket.
    # For P0 stub, grant welcome session:
    welcome = WelcomeFrame(
        heartbeat_s=25,
        user_id=UUID("0192df78-0000-7000-8000-000000000001"),
        device_id=UUID("0192df78-0000-7000-8000-000000000003"),
    )
    await websocket.send_text(welcome.model_dump_json())

    # Step 2: Main frame loop
    try:
        while True:
            text = await websocket.receive_text()
            try:
                frame = json.loads(text)
            except json.JSONDecodeError:
                continue

            frame_type = frame.get("type") if isinstance(frame, dict) else None

            if frame_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif frame_type == "ack":
                # In P1, cursors will be updated in DB and broadcast as receipt
                log.debug("Received ack frame: %s", frame)
            else:
                # Working rule: ignore unknown frame types
                log.debug("Ignored frame type: %s", frame_type)
    except WebSocketDisconnect:
        log.info("WebSocket client disconnected normally")
