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


SWEEP_BATCH = 200


def sweep_pending(
    conn,
    storage,
    enqueue,
    stale_after_s: int = 120,
    expire_after_s: int = 24 * 3600,
    batch: int = SWEEP_BATCH,
) -> dict:
    """Re-queue uploads whose processing task was lost; expire attachments pending for 24 hours.

    A stale row is only re-queued if its object exists, so uploads that never happened
    do not cause endless retries."""
    expired = requeued = 0
    rows = conn.execute(
        "SELECT id, object_key, created_at < now() - make_interval(secs => %s) "
        "FROM attachments WHERE state = 'pending' "
        "AND created_at < now() - make_interval(secs => %s) "
        "ORDER BY created_at LIMIT %s",
        (expire_after_s, stale_after_s, batch),
    ).fetchall()
    for attachment_id, key, is_expired in rows:
        if is_expired:
            changed = conn.execute(
                "UPDATE attachments SET state = 'rejected' WHERE id = %s AND state = 'pending'",
                (attachment_id,),
            ).rowcount
            if changed:
                storage.delete(key)
                storage.delete(f"{key}.thumb")
                expired += 1
        elif storage.object_size(key) is not None:
            enqueue(attachment_id)
            requeued += 1
    return {"expired": expired, "requeued": requeued}


@celery_app.task
def sweep_pending_attachments() -> dict:
    with get_conn() as conn:
        result = sweep_pending(conn, get_storage(), enqueue_processing)
    if result["expired"] or result["requeued"]:
        log.info("attachment sweep", extra={"ctx": result})
    return result