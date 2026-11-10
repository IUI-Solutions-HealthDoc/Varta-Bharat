"""Checks run on an uploaded attachment before it can be sent (pending -> ready/rejected)."""

import hashlib
import io
from uuid import UUID

import filetype
import psycopg
from PIL import Image, ImageOps, UnidentifiedImageError

from app.media.storage import MAX_UPLOAD_BYTES, Storage

THUMB_MAX = 320
MAX_PIXELS = 50_000_000
IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
# The type sniffed from the bytes must match the declared type (or an accepted alias).
ACCEPTED_SNIFFS = {
    "audio/mp4": {"audio/mp4", "audio/m4a", "audio/x-m4a", "video/mp4"},
}


def _reject(conn: psycopg.Connection, storage: Storage, attachment_id: UUID, key: str) -> str:
    conn.execute(
        "UPDATE attachments SET state = 'rejected' WHERE id = %s AND state = 'pending'",
        (attachment_id,),
    )
    storage.delete(key)
    return "rejected"


def _thumbnail(im: Image.Image) -> bytes:
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((THUMB_MAX, THUMB_MAX))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=80)  # re-encoding drops EXIF (e.g. GPS) from the thumbnail
    return out.getvalue()


def process_attachment(conn: psycopg.Connection, storage: Storage, attachment_id: UUID) -> str:
    """Return the attachment's state afterwards. A missing upload leaves it pending."""
    row = conn.execute(
        "SELECT object_key, mime, state FROM attachments WHERE id = %s", (attachment_id,)
    ).fetchone()
    if row is None:
        raise LookupError("attachment not found")
    key, declared, state = row
    if state != "pending":
        return state

    data = storage.get_bytes(key, MAX_UPLOAD_BYTES)
    if data is None:
        return "pending"
    if len(data) == 0 or len(data) > MAX_UPLOAD_BYTES:
        return _reject(conn, storage, attachment_id, key)

    kind = filetype.guess(data)
    sniffed = kind.mime if kind else None
    if sniffed not in ACCEPTED_SNIFFS.get(declared, {declared}):
        return _reject(conn, storage, attachment_id, key)

    width = height = None
    if declared in IMAGE_MIMES:
        try:
            with Image.open(io.BytesIO(data)) as im:
                width, height = im.size
                if width * height > MAX_PIXELS:
                    return _reject(conn, storage, attachment_id, key)
                thumb = _thumbnail(im)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
            return _reject(conn, storage, attachment_id, key)
        storage.put_bytes(f"{key}.thumb", thumb, "image/jpeg")

    conn.execute(
        "UPDATE attachments SET state = 'ready', byte_size = %s, sha256 = %s, "
        "width = %s, height = %s WHERE id = %s AND state = 'pending'",
        (len(data), hashlib.sha256(data).digest(), width, height, attachment_id),
    )
    return "ready"