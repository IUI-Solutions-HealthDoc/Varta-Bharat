"""Attachment downloads: a short-lived presigned GET after an access check."""

from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.auth.authorization import authorize
from app.auth.repository import get_conversation_access
from app.core.db import get_conn
from app.media.deps import AuthUser, current_user
from app.media.processing import IMAGE_MIMES
from app.media.storage import Storage, get_storage

router = APIRouter()

DOWNLOAD_SECONDS = 300
INLINE_PREFIXES = ("image/", "audio/", "video/")


class DownloadOut(BaseModel):
    url: str
    mime: str
    expires_in: int


def _can_read_via_message(conn: psycopg.Connection, user: AuthUser, attachment_id: UUID) -> bool:
    """True if the user is an active member who may see a message carrying the attachment."""
    rows = conn.execute(
        "SELECT DISTINCT m.conversation_id FROM messages m "
        "JOIN conversation_members cm ON cm.conversation_id = m.conversation_id "
        "AND cm.user_id = %s AND cm.left_at IS NULL AND m.seq >= cm.visible_from_seq "
        "WHERE m.attachment_id = %s AND NOT EXISTS ("
        "  SELECT 1 FROM messages d WHERE d.conversation_id = m.conversation_id "
        "  AND d.kind = 'delete' AND d.target_seq = m.seq)",
        (user.id, attachment_id),
    ).fetchall()
    for (conversation_id,) in rows:
        access = get_conversation_access(conn, user.id, user.tenant_id, conversation_id)
        try:
            authorize(user, "read", conversation_id, access)
        except HTTPException:
            continue
        return True
    return False


@router.get("/{attachment_id}/download", response_model=DownloadOut)
def download_attachment(
    attachment_id: UUID,
    response: Response,
    user: Annotated[AuthUser, Depends(current_user)],
    storage: Annotated[Storage, Depends(get_storage)],
    thumb: bool = False,
) -> DownloadOut:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT object_key, mime, uploader_id FROM attachments "
            "WHERE id = %s AND tenant_id = %s AND state = 'ready'",
            (attachment_id, user.tenant_id),
        ).fetchone()
        allowed = row is not None and (
            row[2] == user.id or _can_read_via_message(conn, user, attachment_id)
        )
    if not allowed:  # unknown, other tenant, not ready and not visible all look the same
        raise HTTPException(status_code=404, detail="attachment not found")
    key, mime, _ = row
    if thumb:
        if mime not in IMAGE_MIMES:
            raise HTTPException(status_code=404, detail="no thumbnail")
        key, mime = f"{key}.thumb", "image/jpeg"
    disposition = "inline" if mime.startswith(INLINE_PREFIXES) else "attachment"
    response.headers["Cache-Control"] = "no-store"  # the URL is a bearer capability
    url = storage.presign_get(key, mime, disposition, DOWNLOAD_SECONDS)
    return DownloadOut(url=url, mime=mime, expires_in=DOWNLOAD_SECONDS)