"""Push payload: IDs only (plan D-10). Message text must never go through a push provider."""


def build_payload(tenant_id, conversation_id, seq: int) -> dict[str, str]:
    """Data-message payload. FCM data values must be strings. The device fetches the message
    itself through GET /v1/conversations/{id}/messages."""
    return {
        "tenant_id": str(tenant_id),
        "conversation_id": str(conversation_id),
        "seq": str(seq),
    }