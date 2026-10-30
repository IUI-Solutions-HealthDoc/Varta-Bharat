"""Shared Valkey client (OTPs, ws tickets, pub/sub hints)."""

import valkey

from app.config import settings

_client: valkey.Valkey | None = None


def get_valkey() -> valkey.Valkey:
    global _client
    if _client is None:
        url = settings.valkey_url
        if url.startswith("redis://"):  # .env.example uses the redis:// scheme
            url = "valkey://" + url.removeprefix("redis://")
        _client = valkey.Valkey.from_url(url, decode_responses=True)
    return _client
