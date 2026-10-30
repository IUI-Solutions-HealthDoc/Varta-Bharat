"""Attachment upload endpoints (plan v2: pending row, presigned POST, then complete)."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.db import get_conn
from app.media.deps import AuthUser, current_user
from app.media.storage import MAX_UPLOAD_BYTES, PRESIGN_SECONDS, Storage, get_storage

router = APIRouter(prefix="/v1/attachments", tags=["attachments"])

ALLOWED_MIME = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "audio/mp4",
    "audio/mpeg",
    "audio/ogg",
    "application/pdf",
}


class CreateAttachment(BaseModel):
    mime: str
    byte_size: int = Field(gt=0, le=MAX_UPLOAD_BYTES)

    @field_validator("mime")
    @classmethod
    def _allowed(cls, value: str) -> str:
        value = value.lower()
        if value not in ALLOWED_MIME:
            raise ValueError("unsupported file type")
        return value


class UploadTicket(BaseModel):
    id: UUID
    url: str
    fields: dict[str, str]
    expires_in: int


class AttachmentOut(BaseModel):
    id: UUID
    state: str


@router.post("", response_model=UploadTicket, status_code=201)
def create_attachment(
    body: CreateAttachment,
    user: Annotated[AuthUser, Depends(current_user)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> UploadTicket:
    key = f"{user.tenant_id}/{uuid4()}"  # server-chosen; the client never picks it
    with get_conn() as conn:
        attachment_id = conn.execute(
            "INSERT INTO attachments (tenant_id, uploader_id, object_key, mime, byte_size) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user.tenant_id, user.id, key, body.mime, body.byte_size),
        ).fetchone()[0]
    post = storage.presign_post(key, body.mime)
    return UploadTicket(
        id=attachment_id, url=post["url"], fields=post["fields"], expires_in=PRESIGN_SECONDS
    )


@router.post("/{attachment_id}/complete", response_model=AttachmentOut)
def complete_attachment(
    attachment_id: UUID,
    user: Annotated[AuthUser, Depends(current_user)],
    storage: Annotated[Storage, Depends(get_storage)],
) -> AttachmentOut:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT object_key, state FROM attachments "
            "WHERE id = %s AND tenant_id = %s AND uploader_id = %s",
            (attachment_id, user.tenant_id, user.id),
        ).fetchone()
        if row is None:  # unknown, other tenant and other uploader all look the same
            raise HTTPException(status_code=404, detail="attachment not found")
        key, state = row
        if state != "pending":
            return AttachmentOut(id=attachment_id, state=state)
        size = storage.object_size(key)
        if size is None or size <= 0:
            raise HTTPException(status_code=409, detail="upload not received")
        if size > MAX_UPLOAD_BYTES:
            conn.execute("UPDATE attachments SET state = 'rejected' WHERE id = %s", (attachment_id,))
            return AttachmentOut(id=attachment_id, state="rejected")
        conn.execute("UPDATE attachments SET byte_size = %s WHERE id = %s", (size, attachment_id))
    # Stays pending: the worker (size/MIME/thumbnail checks) is what marks it ready.
    return AttachmentOut(id=attachment_id, state="pending")