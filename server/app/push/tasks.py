"""Celery task for push notifications."""

from uuid import UUID

from app.core.db import get_conn
from app.push.delivery import deliver_push
from app.push.senders import get_sender
from app.worker import celery_app


@celery_app.task
def push_task(conversation_id: str, seq: int) -> dict:
    sender = get_sender()
    if sender is None:
        return {"sent": 0, "dead": 0, "failed": 0}
    with get_conn() as conn:
        return deliver_push(conn, sender, UUID(conversation_id), seq)