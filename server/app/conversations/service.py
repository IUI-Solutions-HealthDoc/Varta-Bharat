from app.auth.dependencies import AuthUser
from app.core.db import get_conn
from app.conversations.repository import create_conversation
from app.conversations.schemas import ConversationCreate


def create_conversation_service(
    user: AuthUser,
    body: ConversationCreate,
) -> dict:

    with get_conn() as conn:
        with conn.transaction():
            return create_conversation(
                conn=conn,
                user=user,
                body=body,
            )