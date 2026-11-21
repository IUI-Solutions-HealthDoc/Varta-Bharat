"""Push providers. A sender returns "ok", "dead" (the token is no longer valid) or "failed"."""

from typing import Protocol

from app.config import settings


class Sender(Protocol):
    def send(self, platform: str, token: str, payload: dict[str, str]) -> str: ...


def get_sender() -> Sender | None:
    """None when push is disabled. Real FCM and APNs senders are added here once credentials
    exist: FCM as a data message, APNs with mutable-content, both carrying only the payload."""
    provider = settings.push_provider
    if provider == "none":
        return None
    raise RuntimeError(f"push provider {provider!r} is not implemented")