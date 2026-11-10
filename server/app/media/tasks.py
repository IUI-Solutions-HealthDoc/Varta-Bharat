"""Background tasks for attachments."""

import logging
from uuid import UUID

from app.core.db import get_conn
from app.media.processing import process_attachment
from app.media.storage import get_storage
from app.worker import celery_app

log = logging.getLogger("varta")


@celery_app.task(bind=True, max_retries=6)
def process_attachment_task(self, attachment_id: str) -> str:
    with get_conn() as conn:
        state = process_attachment(conn, get_storage(), UUID(attachment_id))
    if state == "pending":  # upload not visible yet; try again shortly
        raise self.retry(countdown=10)
    return state


def enqueue_processing(attachment_id: UUID) -> None:
    """Queue processing. A broker outage must not fail the request."""
    try:
        process_attachment_task.delay(str(attachment_id))
    except Exception as exc:
        log.error(
            "could not enqueue attachment processing",
            extra={"ctx": {"error": type(exc).__name__}},
        )