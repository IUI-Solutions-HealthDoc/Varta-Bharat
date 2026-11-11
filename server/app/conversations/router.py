from typing import Annotated

from fastapi import APIRouter, Depends

from app.auth.dependencies import AuthUser, current_user
from app.conversations.schemas import ConversationCreate, ConversationOut
from app.conversations.service import create_conversation_service


router = APIRouter(
    prefix="/v1/conversations",
    tags=["conversations"],
)


@router.post(
    "",
    response_model=ConversationOut,
    status_code=201,
)
def create_conversation_endpoint(
    body: ConversationCreate,
    user: Annotated[AuthUser, Depends(current_user)],
) -> ConversationOut:

    return create_conversation_service(user, body)