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
    recheck_after_s: int = 300,
) -> dict:
    """Re-queue uploads whose processing task was lost; expire attachments pending for 24 hours.

    Expiry is one statement. Re-queue candidates rotate through last_swept_at, so rows whose
    object was never uploaded cannot hold up the ones that were: each row is looked at at most
    once per recheck_after_s."""
    # 1. Expire in one statement and commit it before touching storage.
    with conn.transaction():
        expired_keys = [
            r[0]
            for r in conn.execute(
                "UPDATE attachments SET state = 'rejected' WHERE state = 'pending' "
                "AND created_at < now() - make_interval(secs => %s) RETURNING object_key",
                (expire_after_s,),
            ).fetchall()
        ]
    for key in expired_keys:
        storage.delete(key)
        storage.delete(f"{key}.thumb")

    # 2. Pick the next rows to look at, least recently looked at first, and mark them.
    with conn.transaction():
        rows = conn.execute(
            "SELECT id, object_key FROM attachments WHERE state = 'pending' "
            "AND created_at < now() - make_interval(secs => %s) "
            "AND (last_swept_at IS NULL "
            "     OR last_swept_at < now() - make_interval(secs => %s)) "
            "ORDER BY last_swept_at NULLS FIRST, created_at LIMIT %s "
            "FOR UPDATE SKIP LOCKED",
            (stale_after_s, recheck_after_s, batch),
        ).fetchall()
        if rows:
            conn.execute(
                "UPDATE attachments SET last_swept_at = now() WHERE id = ANY(%s)",
                ([r[0] for r in rows],),
            )

    # 3. Re-queue only the ones whose object really exists.
    requeued = 0
    for attachment_id, key in rows:
        if storage.object_size(key) is not None:
            enqueue(attachment_id)
            requeued += 1
    return {"expired": len(expired_keys), "requeued": requeued}


@celery_app.task
def sweep_pending_attachments() -> dict:
    with get_conn() as conn:
        result = sweep_pending(conn, get_storage(), enqueue_processing)
    if result["expired"] or result["requeued"]:
        log.info("attachment sweep", extra={"ctx": result})
    return result
