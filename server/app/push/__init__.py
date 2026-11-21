"""Push notifications. send_message calls enqueue_push(conversation_id, seq) after commit."""

import logging
from uuid import UUID

from app.config import settings
from app.push import tasks

log = logging.getLogger("varta")


def enqueue_push(conversation_id: UUID, seq: int) -> None:
    """Queue a push for message (conversation_id, seq). Does nothing unless PUSH_PROVIDER is set.
    The short delay lets a connected client's WebSocket ack arrive first (delivered_seq)."""
    if settings.push_provider == "none":
        return
    try:
        tasks.push_task.apply_async(
            args=[str(conversation_id), seq], countdown=settings.push_delay_s
        )
    except Exception as exc:  # noqa: BLE001  a broker outage must not fail a committed send
        log.error("could not enqueue push", extra={"ctx": {"error": type(exc).__name__}})