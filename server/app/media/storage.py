"""S3/MinIO access: presigned uploads and object lookups."""

from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings

MAX_UPLOAD_BYTES = 32 * 1024 * 1024  # matches the attachments.byte_size CHECK
PRESIGN_SECONDS = 900


class Storage:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def presign_post(self, key: str, mime: str) -> dict:
        """Presigned POST: fixed key, fixed content type, 1 byte to 32 MB."""
        return self._client.generate_presigned_post(
            Bucket=settings.s3_bucket,
            Key=key,
            Fields={"Content-Type": mime},
            Conditions=[{"Content-Type": mime}, ["content-length-range", 1, MAX_UPLOAD_BYTES]],
            ExpiresIn=PRESIGN_SECONDS,
        )

    def object_size(self, key: str) -> int | None:
        """Size in bytes of the uploaded object, or None if it does not exist."""
        try:
            head = self._client.head_object(Bucket=settings.s3_bucket, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise
        return head["ContentLength"]


@lru_cache
def get_storage() -> Storage:
    return Storage()